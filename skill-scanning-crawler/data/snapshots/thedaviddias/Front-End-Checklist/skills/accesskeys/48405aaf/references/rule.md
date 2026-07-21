# Ensure accesskey values are unique

> Checks that accesskey values are unique to avoid shortcut conflicts.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
The `accesskey` attribute allows developers to assign keyboard shortcuts to specific elements. To ensure these shortcuts work reliably, each value must be unique within the document.

## Code Example

```html
<!-- ✅ Correct: Unique access keys -->
<a href="/home" accesskey="h">Home</a>
<a href="/contact" accesskey="c">Contact</a>

<!-- ❌ Incorrect: Duplicate access keys -->
<a href="/save" accesskey="s">Save</a>
<a href="/search" accesskey="s">Search</a>
```

## Why It Matters

- **Predictable Navigation**: Ensures keyboard shortcuts work as intended without conflicts.
- **Assistive Technology**: Screen readers and other assistive technologies depend on unique identifiers for reliable interaction.
- **User Experience**: Prevents user frustration when a shortcut doesn't trigger the expected action or moves focus to the wrong element.
- **Browser Consistency**: Different browsers handle duplicate access keys differently; uniqueness ensures a consistent experience across all platforms.

## Exceptions

- Evaluate the rendered experience before treating a static-code smell as a blocker; interaction timing, browser behavior, and assistive technology output often determine severity.
- Not every secondary accessibility issue deserves equal weight; prioritize the issue that most directly blocks perception, operation, or understanding.
- Avoid adding redundant markup or ARIA solely to satisfy a rule when a simpler semantic implementation would eliminate the issue entirely.

## Standards

- Align the implementation with W3C WAI: WCAG Overview and verify the rendered experience, not only the source code.
- Align the implementation with MDN: Accessibility and verify the rendered experience, not only the source code.

## Verification

### Automated Checks

- Inspect the browser accessibility tree or accessibility pane for the relevant element, role, or accessible name.
- Run an automated accessibility checker such as axe or Lighthouse where applicable.

### Manual Checks

- Test the affected UI with keyboard-only navigation and confirm the rule holds in the rendered experience.
- Re-test one representative user flow with a screen reader if this rule affects a key interaction.