# Audit all noindex pages

> Lists and reviews all pages blocked from indexing to ensure critical content is accessible.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
Regularly auditing your `noindex` directives ensures that you are only blocking pages that don't provide search value, such as staging environments, admin panels, or internal search results.

## Code Example

```html
<head>
  <!-- Use this for utility pages like 'Thank You' pages or internal search results -->
  <meta name="robots" content="noindex, follow">
  
  <!-- For pages that should be completely ignored -->
  <meta name="robots" content="noindex, nofollow">
</head>
```

## Why It Matters

- **Visibility**: Prevents accidental exclusion of high-value pages from Google and Bing.
- **Crawl Budget**: Helps search engines focus their limited crawl resources on your most important pages.
- **De-indexing**: Useful for removing outdated or sensitive pages from search results without deleting them.
- **Strategic Control**: Allows you to manage which versions of content (e.g., filtered lists) are available for indexing.

## Exceptions

- Staging, utility, login, account, or internal search pages may intentionally use different crawl or index signals if they are not meant to rank.
- Temporary migration states can produce noisy intermediate signals; flag the live production URL pattern, not one-off transition artifacts.
- When redirects, canonicals, robots directives, or indexability signals conflict, fix the strongest final signal first instead of reporting every downstream symptom as a separate blocker.

## Standards

- Use these references as the standard for the final search-facing HTML, metadata, and crawl behavior.
- Check the implementation against Google Search Central: Search Essentials before treating the rule as satisfied.
- Check the implementation against Google Search Central documentation before treating the rule as satisfied.

## Verification

### Automated Checks

- Inspect rendered HTML and HTTP headers to confirm the expected metadata or crawlability signal is present.
- Test the affected URL with Google Search Console or equivalent tooling where relevant.
- Re-crawl a representative page set after deployment.

### Manual Checks

- Confirm the change does not create conflicting canonical-url, robots, or structured-data signals.