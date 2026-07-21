# Avoid using deprecated ARIA roles

> Checks for deprecated or abstract ARIA roles to ensure long-term compatibility.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
As the WAI-ARIA specification evolves, some roles are deprecated in favor of more precise or better-supported alternatives. Using modern roles ensures your application remains accessible for years to come.

## Code Example

```html
<!-- ✅ Correct: Use modern roles or native elements -->
<nav aria-label="Site">...</nav>
<ul role="list">...</ul>

<!-- ❌ Incorrect: Using deprecated roles -->
<div role="directory">...</div>
```

## Why It Matters

- **Future-Proofing**: Keeps the application compatible with evolving browser and assistive technology (AT) standards.
- **Reliability**: Ensures consistent interpretation of element roles across all platforms and devices.
- **Semantic Accuracy**: Modern roles often provide more precise meaning than older, deprecated ones, leading to a better user experience.
- **Cleaner Code**: Often, a deprecated role can be replaced by a native HTML element (like `<nav>` instead of `role="navigation"`), which is the preferred approach.

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