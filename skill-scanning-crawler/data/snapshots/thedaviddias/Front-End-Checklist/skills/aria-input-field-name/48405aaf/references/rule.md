# Ensure all input fields have accessible names

> Checks that input fields have accessible names so screen reader users know what data each field expects.

**Priority:** critical · **Difficulty:** beginner · **Time:** 10 min

---
Form inputs must be clearly labeled so that users of assistive technology know what information they are expected to provide. [WCAG 2.1 SC 4.1.2](https://www.w3.org/TR/WCAG21/#name-role-value) and the accessible-name computation model both treat that name as required, which is why placeholders are not a substitute for a real label.
## Code Example

```html
<!-- ✅ Correct: <label> with matching for/id — most robust approach -->
<label for="email-address">Email Address</label>
<input type="email" id="email-address" name="email" autocomplete="email">

<!-- ✅ Correct: aria-label for a standalone search input -->
<input type="search" aria-label="Search the knowledge base" name="q">

<!-- ✅ Correct: aria-labelledby references visible heading -->
<h2 id="billing-heading">Billing Address</h2>
<input type="text" aria-labelledby="billing-heading" id="billing-street">

<!-- ❌ Incorrect: placeholder is NOT an accessible name -->
<input type="text" placeholder="Enter your name">

<!-- ❌ Incorrect: visually hidden label text without proper association -->
<span>Username</span>
<input type="text" name="username">
```

## Why It Matters

- **Form Usability**: Screen readers announce the name when focus moves to the field, giving users context before they type.
- **Voice Control**: Dragon NaturallySpeaking users say "click [label text]" to activate fields — the accessible name must match visible text.
- **Error Recovery**: When validation fails, the error message can reference the field name, which only works if the name was defined.
- **AT Navigation**: Screen reader users jump between fields using Tab; the name is the only context they get.

## Accessible Name Computation Order

The browser computes an input's accessible name using this priority order (highest wins):

1. `aria-labelledby` — references another element's text
2. `aria-label` — inline string on the element itself
3. Associated `<label>` element (via `for`/`id` or wrapping)
4. `title` attribute (last resort; also shows as tooltip)
5. `placeholder` — **not a reliable accessible name**

## Exceptions

- Prefer native HTML semantics over ARIA when both are possible; some apparent ARIA failures disappear when the underlying element is corrected.
- A missing ARIA attribute is not automatically the strongest finding if the control is already semantically broken, unnamed, or keyboard-inaccessible.
- Do not add ARIA only to satisfy the rule if the feature should instead be implemented with a native element or a simpler interaction pattern.

## Standards

- Align the implementation with WCAG 2.1 SC 4.1.2: Name, Role, Value and verify the rendered experience, not only the source code.
- Align the implementation with WCAG 2.1 SC 1.3.1: Info and Relationships and verify the rendered experience, not only the source code.
- Align the implementation with WAI-ARIA 1.2: Accessible Name and Description Computation and verify the rendered experience, not only the source code.

## Verification

### Automated Checks

- Inspect the browser accessibility tree or accessibility pane for the relevant element, role, or accessible name.
- Run an automated accessibility checker such as axe or Lighthouse where applicable.

### Manual Checks

- Test the affected UI with keyboard-only navigation and confirm the rule holds in the rendered experience.
- Re-test one representative user flow with a screen reader if this rule affects a key interaction.