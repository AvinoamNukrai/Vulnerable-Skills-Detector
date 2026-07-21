# Provide meaningful alt text for images

> Every informative image has a descriptive alt attribute; decorative images use alt="" to be ignored by screen readers.

**Priority:** critical · **Difficulty:** beginner · **Time:** 15 min

---
The `alt` attribute is the primary accessibility mechanism for images. Every `<img>` must have an `alt` attribute. Its value depends on the image's role.

Use the [W3C alt decision tree](https://www.w3.org/WAI/tutorials/images/decision-tree/) to determine the correct alt value for any image type.

## Code Example

Images that convey meaning need descriptive alt text explaining what the image communicates.

```html
<!-- ❌ Bad: Missing alt -->
<img src="revenue-chart.png">

<!-- ❌ Bad: Filename as alt -->
<img src="revenue-chart.png" alt="revenue-chart.png">

<!-- ❌ Bad: Generic alt -->
<img src="revenue-chart.png" alt="chart">

<!-- ✅ Good: Describes what the image conveys -->
<img
  src="revenue-chart.png"
  alt="Bar chart showing Q3 2024 revenue increased 40% year-over-year, reaching $2.4M"
>
```

## Why It Matters

Approximately 2.2 billion people worldwide have vision impairment. Screen readers read the alt attribute aloud—without meaningful alt text, users who are blind receive no information about image content. Missing alt text also fails WCAG 2.1 Success Criterion 1.1.1, which is a Level A (minimum) requirement. Search engines also rely on alt text to index image content.

## Decorative Images

Images used purely for visual decoration carry no information and should be hidden from assistive technology.

```html
<!-- ❌ Bad: No alt attribute—screen reader may announce the filename -->
<img src="decorative-swirl.png">

<!-- ✅ Good: Empty alt hides image from screen readers -->
<img src="decorative-swirl.png" alt="">

<!-- ✅ Good: Or use CSS background images for decoration -->
<div class="decorative-swirl" aria-hidden="true"></div>
```

## Images Used as Links

When an `<img>` is inside an `<a>`, the alt text must describe the link destination, not the visual appearance.

```html
<!-- ❌ Bad: Describes appearance, not destination -->
<a href="https://twitter.com/example">
  <img src="twitter-logo.svg" alt="Blue bird logo">
</a>

<!-- ✅ Good: Describes the link destination -->
<a href="https://twitter.com/example">
  <img src="twitter-logo.svg" alt="Follow us on Twitter">
</a>
```

## Images of Text

If an image contains text (e.g., a logo, banner, or screenshot), reproduce that text verbatim in alt.

```html
<!-- ✅ Good: Alt reproduces the text shown in the image -->
<img src="sale-banner.png" alt="Summer Sale — 50% off all items">

<!-- ✅ Good: Logo with company name -->
<img src="logo.svg" alt="Acme Corp">
```

## Complex Images (Charts, Diagrams)

For complex visuals, provide a brief alt plus a longer description accessible to all users.

```html
<!-- Using aria-describedby to link to a visible description -->
<figure>
  <img
    src="org-chart.png"
    alt="Company organisational chart"
    aria-describedby="org-chart-desc"
  >
  <figcaption id="org-chart-desc">
    The chart shows three departments reporting to the CEO: Engineering (12 staff),
    Marketing (8 staff), and Operations (5 staff).
  </figcaption>
</figure>
```

## Framework Examples

  

```tsx
interface ImageProps {
  src: string
  alt: string
  decorative?: boolean
}

function AccessibleImage({ src, alt, decorative = false }: ImageProps) {
  return (
    <img
      src={src}
      // Decorative images use empty string; informative images use descriptive text
      alt={decorative ? '' : alt}
    />
  )
}

// Usage

```

  
  

```tsx

// Next.js Image requires alt; use "" for decorative
function HeroBanner() {
  return (
    <>
      {/* Informative */}
      

      {/* Decorative */}
      
    </>
  )
}
```

  

## Standards

- Use these references as the standard for the final image format, delivery, accessibility, and rendering behavior.
- Check the implementation against MDN: Responsive images before treating the rule as satisfied.
- Check the implementation against web.dev: Image performance before treating the rule as satisfied.

## Verification

### Automated Checks

- Run axe DevTools or WAVE on the page—both flag missing or empty non-decorative alt attributes
- Use Lighthouse Accessibility audit—"Images do not have alternate text" is a scored item

### Manual Checks

- Enable a screen reader (VoiceOver, NVDA, or JAWS) and navigate through images with the `G` key
- Inspect the Network tab: for any image URL, verify the corresponding `<img>` has a meaningful `alt`
- **CAPTCHA images** — provide alt describing the purpose, not the characters (e.g., `alt="CAPTCHA: type the characters shown"`), and offer an audio alternative per WCAG 1.1.1
- **SVG icons with adjacent text labels** — if the icon's meaning is already conveyed by visible text, use `aria-hidden="true"` on the SVG instead of alt