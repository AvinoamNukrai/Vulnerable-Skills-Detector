# Provide clear affiliate disclosures

> Checks for affiliate and sponsored content disclosures to maintain transparency.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
Transparency regarding financial incentives is crucial for building a sustainable relationship with your audience and complying with consumer protection laws.

## Code Example

```html
<article>
  <header>
    <h1>The Best Laptops for Developers in 2024</h1>
    <div class="disclosure" style="background: #f9f9f9; padding: 10px; border-radius: 4px;">
      <p><small><em>Disclaimer: This post contains affiliate links. If you click on one and make a purchase, we may receive a small commission at no extra cost to you.</em></small></p>
    </div>
  </header>
  
  <p>Looking for a new laptop? Here are our top recommendations...</p>
</article>
```

## Why It Matters

- **Legal Compliance**: Adheres to FTC (Federal Trade Commission) and other international regulations regarding online advertising.
- **User Trust**: Demonstrates honesty and transparency, which can lead to higher conversion rates over time.
- **SEO Quality**: Prevents being flagged for "sneaky redirects" or hidden affiliate programs that can negatively impact rankings.
- **E-E-A-T**: Supports the "Trust" pillar by showing you aren't hiding financial motivations.

## Exceptions

- Necessary utility or compliance pages can be intentionally brief and should not be judged by the same editorial-depth expectations as ranking-focused content.
- AI-assisted drafting is not a failure by itself; flag unsupported claims, missing editorial review, or low-originality output instead.
- When a page has both trust-signal issues and crawl/index problems, make the page eligible to rank first and then improve the content quality signals.

## Verification

### Automated Checks

- Inspect rendered HTML and HTTP headers to confirm the expected metadata or crawlability signal is present.
- Test the affected URL with Google Search Console or equivalent tooling where relevant.
- Re-crawl a representative page set after deployment.

### Manual Checks

- Confirm the change does not create conflicting canonical-url, robots, or structured-data signals.