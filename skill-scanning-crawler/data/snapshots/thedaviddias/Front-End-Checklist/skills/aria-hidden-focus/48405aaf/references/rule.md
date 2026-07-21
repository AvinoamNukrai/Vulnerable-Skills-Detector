# Remove focusable elements from aria-hidden containers

> Ensures aria-hidden elements do not contain focusable content to avoid "ghost" focus.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
When an element is marked with `aria-hidden="true"`, it is removed from the accessibility tree, but it is **not** removed from the keyboard tab order. [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) makes that distinction explicit, which is why this failure often shows up alongside broader [focus-management issues](/en/rules/accessibility/focus-management).
## Code Example

```html
<!-- ✅ Correct: Focusable element is also removed from tab order -->
<div aria-hidden="true">
  <button tabindex="-1">Hidden Button</button>
</div>

<!-- ✅ Correct: Using the inert attribute (modern browser support) -->
<div inert>
  <button>Hidden Button</button>
</div>

<!-- ❌ Incorrect: Focusable but hidden from AT (Ghost Focus) -->
<div aria-hidden="true">
  <button>I can be focused but not heard</button>
</div>
```

## Why It Matters

- **Avoid Ghost Focus**: Prevents the keyboard focus from disappearing into "silent" regions where no information is announced.
- **User Clarity**: Ensures every focusable element has a corresponding announcement by the screen reader, maintaining user confidence.
- **Logical Flow**: Maintains a consistent and predictable navigation path for keyboard-only users.
- **Reduces Frustration**: Eliminates instances where users might think their browser or the website has crashed because focus seems to have disappeared.

## Exceptions

- Prefer native HTML semantics over ARIA when both are possible; some apparent ARIA failures disappear when the underlying element is corrected.
- A missing ARIA attribute is not automatically the strongest finding if the control is already semantically broken, unnamed, or keyboard-inaccessible.
- Do not add ARIA only to satisfy the rule if the feature should instead be implemented with a native element or a simpler interaction pattern.

## Standards

- Align the implementation with WAI-ARIA 1.2 and verify the rendered experience, not only the source code.
- Align the implementation with MDN: ARIA and verify the rendered experience, not only the source code.

## Support Notes

- The `inert` attribute is the cleanest modern fix, but older browser targets may still need a fallback that removes descendants from the tab order manually.
- Verify the rendered focus behavior in the project target browsers because browser and assistive-technology combinations still differ in how they expose hidden content.

## Verification

### Automated Checks

- Inspect the browser accessibility tree or accessibility pane for the relevant element, role, or accessible name.
- Run an automated accessibility checker such as axe or Lighthouse where applicable.

### Manual Checks

- Test the affected UI with keyboard-only navigation and confirm the rule holds in the rendered experience.
- Re-test one representative user flow with a screen reader if this rule affects a key interaction.