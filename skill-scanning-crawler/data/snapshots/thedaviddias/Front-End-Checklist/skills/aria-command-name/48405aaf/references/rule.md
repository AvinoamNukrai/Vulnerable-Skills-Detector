# Provide accessible names for ARIA command elements

> Checks that command elements like buttons and links have accessible names for screen reader support.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
Command elements are interactive controls that perform an action. For these to be usable by everyone, they must have a programmatically determinable name that describes their function.

## Code Example

```html
<!-- ✅ Correct: Accessible name via text content -->
<button>Submit Form</button>

<!-- ✅ Correct: Accessible name via aria-label (for icon buttons) -->
<button aria-label="Close dialog">
  <svg>...</svg>
</button>

<!-- ❌ Incorrect: No accessible name (empty or icon-only without label) -->
<button>
  <i class="fa fa-trash"></i>
</button>
```

## Why It Matters

- **Clarity**: Informs users exactly what action will be performed when the element is activated.
- **Navigability**: Allows users to find and activate controls via voice commands or by browsing lists of controls in their screen reader.
- **Inclusion**: Provides a comparable experience for users who cannot see visual icons or cues.
- **Avoids Confusion**: Prevents the "unlabeled button" experience, which is one of the most common accessibility barriers.

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