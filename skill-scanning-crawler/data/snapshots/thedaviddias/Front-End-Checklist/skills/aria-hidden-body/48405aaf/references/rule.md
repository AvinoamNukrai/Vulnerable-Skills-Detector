# Do not use aria-hidden on the document body

> Ensures the document body is not set to aria-hidden, which would hide the entire page from screen readers.

**Priority:** critical · **Difficulty:** intermediate · **Time:** 10 min

---
The `aria-hidden` attribute removes an element and all of its children from the accessibility tree. Applying it to the `<body>` tag makes your entire website non-existent for screen reader users.

## Code Example

```html
<!-- ✅ Correct: Hidden attribute on background content only -->
<body>
  <div id="app-root" aria-hidden="true">
    <!-- Main content hidden while modal is open -->
  </div>
  <div id="modal-portal">
    <!-- Modal remains visible to AT -->
  </div>
</body>

<!-- ❌ Incorrect: aria-hidden on body -->
<body aria-hidden="true">
  <h1>This whole page is invisible to a screen reader</h1>
</body>
```

## Why It Matters

- **Full Inaccessibility**: Hides every single piece of content and interactive element from screen readers.
- **Broken Experience**: Users cannot navigate, read, or interact with any part of the application.
- **Common Implementation Bug**: Frequently caused by automated scripts or libraries that try to "lock" the background when a modal is open but target the wrong element.
- **Critical Failure**: This is considered a high-priority accessibility violation that prevents access to the entire service.

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