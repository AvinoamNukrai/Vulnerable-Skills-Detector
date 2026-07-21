# Make accordions keyboard navigable

> Accordion components use proper ARIA attributes and keyboard interactions for screen reader accessibility.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 25 min

---
Accessible accordions allow users to efficiently navigate and reveal content sections using any input method.

## Code Example

```html
<div class="accordion">
  <h3>
    <button
      type="button"
      aria-expanded="false"
      aria-controls="panel-1"
      class="accordion__trigger"
      id="accordion-1"
    >
      Section 1
      <span class="accordion__icon" aria-hidden="true"></span>
    </button>
  </h3>
  <div
    id="panel-1"
    role="region"
    aria-labelledby="accordion-1"
    class="accordion__panel"
    hidden
  >
    <p>Panel 1 content goes here.</p>
  </div>

  <h3>
    <button
      type="button"
      aria-expanded="false"
      aria-controls="panel-2"
      class="accordion__trigger"
      id="accordion-2"
    >
      Section 2
      <span class="accordion__icon" aria-hidden="true"></span>
    </button>
  </h3>
  <div
    id="panel-2"
    role="region"
    aria-labelledby="accordion-2"
    class="accordion__panel"
    hidden
  >
    <p>Panel 2 content goes here.</p>
  </div>
</div>
```

## Why It Matters

Poorly implemented accordions trap keyboard users and leave screen reader users unable to understand or navigate collapsed content sections.

## ARIA Pattern Requirements

| Element | Attribute | Purpose |
|---------|-----------|---------|
| Trigger | `button` element | Activatable with Enter/Space |
| Trigger | `aria-expanded` | Indicates open/closed state |
| Trigger | `aria-controls` | References panel ID |
| Panel | `id` | Target of aria-controls |
| Panel | `role="region"` | Optional, for important sections |
| Header | Heading element | Maintains document structure |

## React Accordion Component

```tsx

interface AccordionItemProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

interface AccordionProps {
  children: React.ReactNode
  allowMultiple?: boolean
}

  const [openItems, setOpenItems] = useState { itemRefs.current[index] = el },
          } as any)
        }
        return child
      })}
    </div>
  )
}

  title,
  children,
  defaultOpen = false,
  _index,
  _isOpen,
  _onToggle,
  _onKeyDown,
  _ref,
}: AccordionItemProps & {
  _index?: number
  _isOpen?: boolean
  _onToggle?: () => void
  _onKeyDown?: (e: KeyboardEvent) => void
  _ref?: (el: HTMLButtonElement) => void
}) {
  const triggerId = useId()
  const panelId = useId()
  const isOpen = _isOpen ?? defaultOpen

  return (
    <div className="accordion__item">
      <h3 className="accordion__header">
        <button
          ref={_ref}
          type="button"
          id={triggerId}
          aria-expanded={isOpen}
          aria-controls={panelId}
          onClick={_onToggle}
          onKeyDown={_onKeyDown}
          className="accordion__trigger"
        >
          <span className="accordion__title">{title}</span>
          <span
            className={`accordion__icon ${isOpen ? 'accordion__icon--open' : ''}`}
            aria-hidden="true"
          />
        </button>
      </h3>
      <div
        id={panelId}
        role="region"
        aria-labelledby={triggerId}
        className="accordion__panel"
        hidden={!isOpen}
      >
        <div className="accordion__content">
          {children}
        </div>
      </div>
    </div>
  )
}
```

## Usage

```tsx
You can return items within 30 days of purchase...</p>
  
  
    <p>Standard shipping takes 5-7 business days...</p>
  
  
    <p>Yes, we ship to over 50 countries...</p>
  

```

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `Enter` / `Space` | Toggle panel open/closed |
| `Arrow Down` | Move focus to next header |
| `Arrow Up` | Move focus to previous header |
| `Home` | Move focus to first header |
| `End` | Move focus to last header |

## Native HTML Details/Summary

```html
<!-- Simple native accordion (limited styling) -->
<details class="accordion-native">
  <summary>Section Title</summary>
  <div class="accordion-native__content">
    <p>Content here...</p>
  </div>
</details>

<details class="accordion-native">
  <summary>Another Section</summary>
  <div class="accordion-native__content">
    <p>More content...</p>
  </div>
</details>
```

```tsx
// React wrapper for details/summary
function NativeAccordion({ title, children, defaultOpen = false }) {
  return (
    <details open={defaultOpen} className="accordion-native">
      <summary>{title}</summary>
      <div className="accordion-native__content">
        {children}
      </div>
    </details>
  )
}
```

## Styling

```css
.accordion {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.accordion__item {
  border-bottom: 1px solid #e0e0e0;
}

.accordion__item:last-child {
  border-bottom: none;
}

.accordion__header {
  margin: 0;
}

.accordion__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 1rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  text-align: left;
  background: #fff;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
}

.accordion__trigger:hover {
  background: #f5f5f5;
}

.accordion__trigger:focus-visible {
  outline: 2px solid #0066cc;
  outline-offset: -2px;
}

.accordion__icon {
  width: 1.25rem;
  height: 1.25rem;
  transition: transform 0.2s;
}

.accordion__trigger[aria-expanded="true"] .accordion__icon {
  transform: rotate(180deg);
}

.accordion__panel[hidden] {
  display: none;
}

.accordion__content {
  padding: 0 1.5rem 1rem;
}

/* Animation */
.accordion__panel {
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .accordion__panel,
  .accordion__icon {
    animation: none;
    transition: none;
  }
}
```

## Verification

1. Tab to first accordion header
2. Press Enter/Space to toggle
3. Use Arrow keys to navigate between headers
4. Press Home/End to jump to first/last
5. Test with screen reader (announces expanded state)
6. Verify heading structure in accessibility tree
7. Check focus is visible on all interactive elements

Choose an appropriate heading level (h2, h3, etc.) based on the accordion's position in the document outline. Don't skip heading levels.