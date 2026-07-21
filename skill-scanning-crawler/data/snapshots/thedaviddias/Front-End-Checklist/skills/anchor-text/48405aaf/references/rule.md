# Use descriptive anchor text

> Checks for descriptive, keyword-rich anchor text that provides context for users and search engines.

**Priority:** medium · **Difficulty:** beginner · **Time:** 5 min

---
Anchor text is the clickable text in a hyperlink. It should provide a clear indication of what the user will find when they click the link.

## Code Example

```html
<!-- ✅ Good: Descriptive and contextual -->
<p>For more information, read our <a href="/seo-guide">complete guide to SEO best practices</a>.</p>

<!-- ❌ Bad: Generic and provides no context -->
<p>To learn more about our SEO services, <a href="/seo-guide">click here</a>.</p>
```

## Why It Matters

- **Search Context**: Tells search engines what the linked page is about, helping it rank for those terms.
- **Accessibility**: Screen reader users often navigate via a list of links; descriptive text makes this list meaningful.
- **User Trust**: Users are more likely to click a link when they know exactly where it leads.
- **Internal Navigation**: Helps distribute authority throughout your site by creating a logical web of related content.

## Exceptions

- Utility or intentionally noindex pages may keep minimal metadata when richer search presentation is not a goal.
- Template-driven pages can look repetitive in isolation; confirm the fully rendered production output before flagging duplication or omission.
- If a page is intentionally redirected or excluded from indexation, resolve that crawlability decision before treating metadata polish as the primary issue.

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