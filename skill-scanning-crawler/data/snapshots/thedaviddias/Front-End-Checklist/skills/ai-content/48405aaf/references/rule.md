# Audit and refine AI-generated content

> Detects and reviews content that appears to be primarily AI-generated to ensure quality.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
While AI tools can assist in the writing process, the final output still has to satisfy [Google's Search Essentials](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) and deliver the depth expected from [high-quality content](/en/rules/seo/quality) that genuinely helps the reader.

## Code Example

While there's no "code" to detect AI, you can signal human involvement and expertise in your metadata and bylines.

```html
<article>
  <header>
    <h1>Advanced TypeScript Patterns</h1>
    <div class="meta">
      <span>By Jane Smith, Senior Engineer</span>
      <span>Fact-checked on October 20, 2023</span>
    </div>
  </header>
  
  <p>In this article, we'll explore patterns I've used in production at ScaleTech...</p>
</article>
```

## Why It Matters

- **Quality Standards**: Google's guidance on [creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) targets low-value automation that does not add original insight.
- **Accuracy**: AI can hallucinate facts; human verification is essential for [YMYL content](/en/rules/seo/ymyl-detection), where bad advice can cause real harm.
- **Uniqueness**: Prevents your site from becoming a "carbon copy" of other sites using the same AI prompts.
- **User Experience**: Human-edited content is generally more engaging, nuanced, and better at solving specific user problems.

If a draft feels generic, unsupported, or too close to what a model would produce by default, review it alongside thin-content risk before deciding it is ready to publish.

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