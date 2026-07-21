# Create a dedicated About page

> Checks for a dedicated about or company page with meaningful content.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
An About page provides essential context about the source of the information on your website. It helps search engines and users understand the expertise and authority behind the content.

## Code Example

Ensure the About page is easily discoverable, typically via the main navigation or the footer.

```html
<footer>
  <nav aria-label="Footer Navigation">
    <ul>
      <li><a href="/about">About Us</a></li>
      <li><a href="/contact">Contact</a></li>
      <li><a href="/privacy-policy">Privacy Policy</a></li>
    </ul>
  </nav>
</footer>
```

## Why It Matters

- **E-E-A-T**: Directly supports the Trustworthiness and Authoritativeness pillars of Google's Quality Rater Guidelines.
- **Transparency**: Shows users who you are, reducing bounce rates and building long-term brand loyalty.
- **Entity Recognition**: Helps search engines connect your website to a real-world entity (person or organization).
- **Compliance**: For many industries, identifying the content creator is a legal or regulatory requirement.

## Exceptions

- Necessary utility or compliance pages can be intentionally brief and should not be judged by the same editorial-depth expectations as ranking-focused content.
- AI-assisted drafting is not a failure by itself; flag unsupported claims, missing editorial review, or low-originality output instead.
- When a page has both trust-signal issues and crawl/index problems, make the page eligible to rank first and then improve the content quality signals.

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