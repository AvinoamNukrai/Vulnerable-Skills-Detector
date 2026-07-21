# Use only allowed ARIA attributes for each role

> Checks that ARIA attributes are allowed on their elements to ensure valid accessibility trees.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
ARIA (Accessible Rich Internet Applications) attributes must match the role of the element they are applied to. Using attributes that don't belong to a role can result in "silent" failures where accessibility information is lost.

## Code Example

```html
<!-- ✅ Correct: aria-checked is allowed on checkbox role -->
<div role="checkbox" aria-checked="true" tabindex="0">Subscribe</div>

<!-- ❌ Incorrect: aria-checked is NOT allowed on a heading role -->
<h1 role="heading" aria-checked="true">Main Title</h1>
```

## Why It Matters

- **Standard Compliance**: Adheres to WAI-ARIA specifications for robust and predictable web applications.
- **AT Accuracy**: Guarantees that assistive technologies receive correct and relevant information about the element's state.
- **Reduced Noise**: Prevents developers from adding redundant, invalid, or confusing metadata to the DOM.
- **Future Compatibility**: Valid ARIA usage ensures that your application remains accessible as browser and screen reader implementations evolve.

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