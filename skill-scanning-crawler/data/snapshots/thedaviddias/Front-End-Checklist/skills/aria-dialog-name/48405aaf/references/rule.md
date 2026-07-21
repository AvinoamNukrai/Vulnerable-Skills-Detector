# Ensure dialogs have an accessible name

> Checks that dialog elements have accessible names to orient screen reader users.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
Dialogs (modals) interrupt the user's flow. To provide a smooth transition for assistive technology users, the dialog must identify itself as soon as it gains focus.

## Code Example

```html
<!-- ✅ Correct: Using aria-labelledby to point to the header -->
<div role="dialog" aria-labelledby="modal-title" aria-modal="true">
  <h2 id="modal-title">Edit Profile</h2>
  <form>...</form>
</div>

<!-- ✅ Correct: Using aria-label for a simple notification -->
<div role="alertdialog" aria-label="Session Timeout" aria-modal="true">
  <p>Your session is about to expire.</p>
  <button>Stay logged in</button>
</div>

<!-- ❌ Incorrect: No accessible name -->
<div role="dialog">
  <p>Some content without a title...</p>
</div>
```

## Why It Matters

- **Orientation**: Helps users immediately understand they have entered a new context or "window."
- **Context**: Clearly states the purpose of the dialog (e.g., "Confirm Deletion") before the user starts interacting with its contents.
- **Compliance**: Follows WAI-ARIA best practices for accessible modal windows and user interface patterns.
- **Efficiency**: Allows users to decide whether to interact with or dismiss the dialog based on its title alone.

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