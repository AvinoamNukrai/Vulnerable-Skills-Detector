"""Async GitHub REST v3 client.

Never hardcodes tokens — token must come from an environment variable.
Never logs token values.

Usage::

    async with GitHubClient.from_config(cfg, cache) as client:
        repos = await client.search_repositories("SKILL.md in:path")
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any, cast

import httpx

from skill_scanning_crawler.common.config import CrawlerConfig, RateLimitsConfig
from skill_scanning_crawler.common.exceptions import GitHubClientError, RateLimitError
from skill_scanning_crawler.github_client.cache import GitHubCache
from skill_scanning_crawler.github_client.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com"
_ACCEPT_V3 = "application/vnd.github+json"
_ACCEPT_RAW = "application/vnd.github.v3.raw"
_API_VERSION = "2022-11-28"


class GitHubClient:
    """Async GitHub REST v3 client with rate limiting, retry, and cache."""

    def __init__(
        self,
        token: str | None,
        cache: GitHubCache | None = None,
        rate_limiter: RateLimiter | None = None,
        timeout: int = 30,
    ) -> None:
        # Token stored but never logged.
        self._token = token
        self._cache = cache
        self._rate_limiter = rate_limiter or RateLimiter()
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        config: CrawlerConfig,
        cache: GitHubCache | None = None,
    ) -> GitHubClient:
        token_env = config.github.token_env_var
        token = os.environ.get(token_env)
        rl_cfg: RateLimitsConfig = config.rate_limits
        rl = RateLimiter(
            search_concurrency=rl_cfg.search_concurrency,
            metadata_concurrency=rl_cfg.metadata_concurrency,
            tree_concurrency=rl_cfg.tree_concurrency,
            download_concurrency=rl_cfg.download_concurrency,
            max_retries=rl_cfg.max_retries,
            backoff_initial=rl_cfg.backoff_initial_seconds,
            backoff_max=rl_cfg.backoff_max_seconds,
        )
        return cls(
            token=token,
            cache=cache,
            rate_limiter=rl,
            timeout=config.github.request_timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> GitHubClient:
        headers: dict[str, str] = {
            "Accept": _ACCEPT_V3,
            "X-GitHub-Api-Version": _API_VERSION,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=headers,
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Low-level request with retry + rate-limit awareness
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        category: str = "metadata",
        params: dict[str, Any] | None = None,
        accept: str | None = None,
    ) -> httpx.Response:
        if self._http is None:
            raise GitHubClientError(
                "GitHubClient must be used as an async context manager"
            )
        sem = self._rate_limiter.semaphore(category)
        rl = self._rate_limiter
        last_exc: Exception = GitHubClientError("No attempts made")

        for attempt in range(rl.max_retries + 1):
            async with sem:
                try:
                    extra_headers: dict[str, str] = {}
                    if accept:
                        extra_headers["Accept"] = accept
                    resp = await self._http.request(
                        method, path, params=params, headers=extra_headers
                    )
                    rl.log_rate_limit_headers(resp)

                    if resp.status_code == 200:
                        return resp

                    if resp.status_code in (403, 429):
                        retry_after_str = resp.headers.get("retry-after")
                        if retry_after_str:
                            wait = float(retry_after_str)
                            log.warning(
                                "Rate-limited (Retry-After); sleeping %.1fs path=%s",
                                wait, path,
                            )
                        else:
                            wait = rl.backoff_delay(attempt)
                            log.warning(
                                "Rate-limited (HTTP %d); retry %d/%d, sleeping %.1fs path=%s",
                                resp.status_code, attempt + 1, rl.max_retries, wait, path,
                            )
                        await asyncio.sleep(wait)
                        last_exc = RateLimitError(
                            f"HTTP {resp.status_code} rate limit on {path}"
                        )
                        continue

                    if resp.status_code == 404:
                        raise GitHubClientError(f"Not found: {path}")

                    if resp.status_code >= 500:
                        wait = rl.backoff_delay(attempt)
                        log.warning(
                            "Server error %d; retry %d/%d, sleeping %.1fs path=%s",
                            resp.status_code, attempt + 1, rl.max_retries, wait, path,
                        )
                        await asyncio.sleep(wait)
                        last_exc = GitHubClientError(
                            f"HTTP {resp.status_code} from {path}"
                        )
                        continue

                    raise GitHubClientError(
                        f"Unexpected HTTP {resp.status_code} from {path}"
                    )

                except httpx.HTTPError as exc:
                    # Broadened from (TimeoutException, NetworkError) to the httpx
                    # base class so protocol-level failures (e.g. RemoteProtocolError,
                    # which is an HTTPError but NOT a NetworkError) are retried and
                    # ultimately surface as GitHubClientError, rather than escaping
                    # the client and aborting an entire pipeline stage.
                    wait = rl.backoff_delay(attempt)
                    log.warning(
                        "Transport error %s; retry %d/%d, sleeping %.1fs path=%s",
                        type(exc).__name__, attempt + 1, rl.max_retries, wait, path,
                    )
                    await asyncio.sleep(wait)
                    last_exc = GitHubClientError(str(exc))

        raise GitHubClientError(
            f"All {rl.max_retries} retries exhausted for {path}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_code(
        self,
        query: str,
        per_page: int = 100,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Return code-search items matching *query*."""
        cache_key = ("search_code", query, str(per_page), str(max_pages))
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return cast(list[dict[str, Any]], hit)

        items: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            resp = await self._request(
                "GET", "/search/code",
                category="search",
                params={"q": query, "per_page": per_page, "page": page},
            )
            page_items: list[dict[str, Any]] = resp.json().get("items", [])
            items.extend(page_items)
            if len(page_items) < per_page:
                break
            await asyncio.sleep(2)  # secondary rate limit courtesy pause

        if self._cache:
            self._cache.set(items, *cache_key, ttl=3600)
        return items

    async def search_repositories(
        self,
        query: str,
        per_page: int = 100,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Return repository-search items matching *query*."""
        cache_key = ("search_repos", query, str(per_page), str(max_pages))
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return cast(list[dict[str, Any]], hit)

        items: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            resp = await self._request(
                "GET", "/search/repositories",
                category="search",
                params={"q": query, "per_page": per_page, "page": page},
            )
            page_items = resp.json().get("items", [])
            items.extend(page_items)
            if len(page_items) < per_page:
                break
            await asyncio.sleep(2)

        if self._cache:
            self._cache.set(items, *cache_key, ttl=3600)
        return items

    # ------------------------------------------------------------------
    # Repository metadata
    # ------------------------------------------------------------------

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Return the GitHub REST repository object for *owner*/*repo*."""
        cache_key = ("repo_meta", owner, repo)
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return cast(dict[str, Any], hit)

        resp = await self._request("GET", f"/repos/{owner}/{repo}")
        data: dict[str, Any] = resp.json()
        if self._cache:
            self._cache.set(data, *cache_key, ttl=3600)
        return data

    async def get_default_branch_sha(
        self, owner: str, repo: str, branch: str
    ) -> str:
        """Return the latest commit SHA on *branch*."""
        cache_key = ("branch_sha", owner, repo, branch)
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return str(hit)

        resp = await self._request(
            "GET", f"/repos/{owner}/{repo}/commits/{branch}"
        )
        sha: str = resp.json()["sha"]
        if self._cache:
            self._cache.set(sha, *cache_key, ttl=300)
        return sha

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    async def get_tree(
        self,
        owner: str,
        repo: str,
        tree_sha: str,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """Return the flat file tree at *tree_sha*."""
        cache_key = ("tree", owner, repo, tree_sha)
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return cast(list[dict[str, Any]], hit)

        params: dict[str, str] = {"recursive": "1"} if recursive else {}
        resp = await self._request(
            "GET", f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            category="tree",
            params=params,
        )
        payload = resp.json()
        tree: list[dict[str, Any]] = payload.get("tree", [])
        # GitHub caps recursive trees at 100k entries and sets truncated=true.
        # Without surfacing this, SKILL.md files (and auxiliary files) past the
        # cap are silently missed. Warn so large-repo under-scanning is visible;
        # full pagination of truncated trees is a documented follow-up.
        if payload.get("truncated"):
            log.warning(
                "Tree TRUNCATED for %s/%s@%s (>100k entries); some files may be "
                "missed. Consider per-subtree fetching for this repo.",
                owner, repo, tree_sha[:8],
            )
        if self._cache:
            self._cache.set(tree, *cache_key, ttl=3600)
        return tree

    # ------------------------------------------------------------------
    # File content
    # ------------------------------------------------------------------

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> str:
        """Return decoded UTF-8 text of *path* at *ref*."""
        cache_key = ("file_content", owner, repo, path, ref)
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return str(hit)

        resp = await self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        data = resp.json()
        encoding: str = data.get("encoding", "base64")
        if encoding == "base64":
            raw_content = base64.b64decode(
                data["content"].replace("\n", "")
            ).decode("utf-8", errors="replace")
        else:
            raw_content = str(data.get("content", ""))

        if self._cache:
            self._cache.set(raw_content, *cache_key, ttl=3600)
        return raw_content

    async def get_raw_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> bytes:
        """Return raw bytes of *path* at *ref*."""
        cache_key = ("raw_content", owner, repo, path, ref)
        if self._cache:
            hit = self._cache.get(*cache_key)
            if hit is not None:
                return bytes(hit)

        resp = await self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{path}",
            category="download",
            params={"ref": ref},
            accept=_ACCEPT_RAW,
        )
        raw = resp.content
        if self._cache:
            self._cache.set(raw, *cache_key, ttl=3600)
        return raw
