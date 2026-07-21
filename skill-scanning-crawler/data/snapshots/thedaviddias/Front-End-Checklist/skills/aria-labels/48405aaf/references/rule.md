# Provide accessible names for all interactive elements

> Checks that interactive elements have accessible names for clear navigation.

**Priority:** high · **Difficulty:** intermediate · **Time:** 10 min

---
Every interactive element on a page must communicate its purpose to assistive technologies. [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) treats accessible naming as foundational for buttons, links, and widgets, which is why this rule often overlaps with [ARIA command names](/en/rules/accessibility/aria-command-name).
## Code Example

```html
<!-- ✅ Correct: Descriptive label for icon button -->
<button aria-label="Download PDF report">
  <i class="icon-download"></i>
</button>

<!-- ✅ Correct: Descriptive link text -->
<a href="/pricing">View our subscription plans</a>

<!-- ❌ Incorrect: Non-descriptive label (Too generic) -->
<a href="/article/123">Read more</a>

<!-- ❌ Incorrect: No label (Icon-only without description) -->
<button>
  <span class="glyph-print"></span>
</button>
```

## Why It Matters

- **Efficiency**: Helps users quickly scan and find the right control when using a screen reader's "elements list."
- **Searchability**: Clear labels are vital for users who navigate via voice control, as they need to speak the name of the control to activate it.
- **Clarity**: Removes ambiguity about what will happen when a control is activated, reducing user anxiety and errors.
- **Consistency**: Ensures that the experience for screen reader users matches the visual intent of the design.

## Exceptions

- Prefer native HTML semantics over ARIA when both are possible; some apparent ARIA failures disappear when the underlying element is corrected.
- A missing ARIA attribute is not automatically the strongest finding if the control is already semantically broken, unnamed, or keyboard-inaccessible.
- Do not add ARIA only to satisfy the rule if the feature should instead be implemented with a native element or a simpler interaction pattern.

## Standards

- Align the implementation with WAI-ARIA 1.2 and verify the rendered experience, not only the source code.
- Align the implementation with MDN: ARIA and verify the rendered experience, not only the source code.

## Verification

### Automated Checks

- Inspect the browser accessibility tree or accessibility pane for the relevant element, role, or accessible name.
- Run an automated accessibility checker such as axe or Lighthouse where applicable.

### Manual Checks

- Test the affected UI with keyboard-only navigation and confirm the rule holds in the rendered experience.
- Re-test one representative user flow with a screen reader if this rule affects a key interaction.