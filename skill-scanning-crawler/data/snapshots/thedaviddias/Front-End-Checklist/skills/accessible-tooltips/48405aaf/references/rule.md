# Create accessible tooltips

> Tooltips are accessible to keyboard users and screen readers with proper ARIA attributes and focus handling.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 20 min

---
Accessible tooltips provide supplementary information without excluding keyboard or screen reader users.

## Code Example

```html
<div class="tooltip-container">
  <button
    type="button"
    aria-describedby="tooltip-1"
    class="tooltip-trigger"
  >
    Settings
  </button>
  <div
    id="tooltip-1"
    role="tooltip"
    class="tooltip"
  >
    Configure your preferences
  </div>
</div>
```

## Why It Matters

Inaccessible tooltips leave keyboard and screen reader users without important contextual information, creating an unequal experience and potential confusion.

## Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| Keyboard accessible | Show on focus, not just hover |
| Programmatically associated | Use `aria-describedby` |
| Dismissible | Close with Escape key |
| Persistent | Stay visible while hovered/focused |
| Non-essential | Don't hide critical info in tooltips |

## React Tooltip Component

```tsx

interface TooltipProps {
  content: string
  children: React.ReactElement
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}

  content,
  children,
  position = 'top',
  delay = 300
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const tooltipId = useId()
  const timeoutRef = useRef {
    clearTimeout(timeoutRef.current)
    setIsVisible(false)
  }

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isVisible) {
        hideTooltip()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isVisible])

  // Clone child to add props
  const trigger = React.cloneElement(children, {
    ref: triggerRef,
    'aria-describedby': isVisible ? tooltipId : undefined,
    onMouseEnter: showTooltip,
    onMouseLeave: hideTooltip,
    onFocus: showTooltip,
    onBlur: hideTooltip,
  })

  return (
    <div className="tooltip-wrapper">
      {trigger}
      {isVisible && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`tooltip tooltip--${position}`}
        >
          {content}
        </div>
      )}
    </div>
  )
}
```

## Usage

```tsx

  <button type="button">
    
    <span className="sr-only">Save</span>
  </button>

  <label htmlFor="email">
    Email <span aria-hidden="true">*</span>
  </label>

```

## Advanced Tooltip with Floating UI

```tsx

interface AdvancedTooltipProps {
  content: React.ReactNode
  children: React.ReactElement
}

  const [isOpen, setIsOpen] = useState(false)
  const arrowRef = useRef(null)
  const tooltipId = useId()

  const { refs, floatingStyles, context } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement: 'top',
    middleware: [
      offset(8),
      flip(),
      shift({ padding: 8 }),
      arrow({ element: arrowRef })
    ],
  })

  return (
    <>
      {React.cloneElement(children, {
        ref: refs.setReference,
        'aria-describedby': isOpen ? tooltipId : undefined,
        onMouseEnter: () => setIsOpen(true),
        onMouseLeave: () => setIsOpen(false),
        onFocus: () => setIsOpen(true),
        onBlur: () => setIsOpen(false),
      })}

      {isOpen && (
        <div
          ref={refs.setFloating}
          id={tooltipId}
          role="tooltip"
          style={floatingStyles}
          className="tooltip"
        >
          {content}
          <div ref={arrowRef} className="tooltip-arrow" />
        </div>
      )}
    </>
  )
}
```

## Icon Button with Tooltip

```tsx
interface IconButtonProps {
  icon: React.ReactNode
  label: string
  onClick: () => void
  tooltip?: string
}

  const tooltipId = useId()
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="icon-button-wrapper">
      <button
        type="button"
        onClick={onClick}
        aria-label={label}
        aria-describedby={tooltip && showTooltip ? tooltipId : undefined}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        className="icon-button"
      >
        {icon}
      </button>

      {tooltip && showTooltip && (
        <span id={tooltipId} role="tooltip" className="tooltip">
          {tooltip}
        </span>
      )}
    </div>
  )
}
```

## Native Title Attribute (Limited)

```html
<!-- Simple but limited accessibility -->
<button type="button" title="Save document">
  <svg aria-hidden="true"><!-- save icon --></svg>
  <span class="sr-only">Save</span>
</button>

<!-- Better: Custom tooltip with full control -->
<button
  type="button"
  aria-describedby="save-tooltip"
  aria-label="Save"
>
  <svg aria-hidden="true"><!-- save icon --></svg>
</button>
<div id="save-tooltip" role="tooltip" class="tooltip">
  Save document (Ctrl+S)
</div>
```

## Styling

```css
.tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.tooltip {
  position: absolute;
  z-index: 1000;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  background: #1a1a1a;
  color: #ffffff;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;

  /* Animation */
  opacity: 0;
  animation: tooltipFadeIn 0.15s ease-out forwards;
}

.tooltip--top {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 8px;
}

.tooltip--bottom {
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 8px;
}

.tooltip--left {
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-right: 8px;
}

.tooltip--right {
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-left: 8px;
}

/* Arrow */
.tooltip::after {
  content: '';
  position: absolute;
  border: 6px solid transparent;
}

.tooltip--top::after {
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-top-color: #1a1a1a;
}

@keyframes tooltipFadeIn {
  from { opacity: 0; transform: translateX(-50%) translateY(4px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .tooltip {
    animation: none;
    opacity: 1;
  }
}

/* Ensure sufficient contrast */
.tooltip {
  /* WCAG requires 4.5:1 for normal text */
  /* #ffffff on #1a1a1a = 16.1:1 ✓ */
}
```

## When to Use Tooltips vs Other Patterns

| Use Case | Pattern |
|----------|---------|
| Supplementary hint | Tooltip |
| Essential instruction | Inline text |
| Complex content | Popover/Dialog |
| Form field help | `aria-describedby` text |
| Icon-only button | `aria-label` + optional tooltip |

## Verification

1. Tab to trigger element - tooltip should appear
2. Press Escape - tooltip should close
3. Hover over trigger - tooltip appears after delay
4. Move mouse to tooltip - should stay visible
5. Test with screen reader (tooltip content announced)
6. Verify tooltip doesn't block other content
7. Check color contrast meets WCAG requirements

Never put essential information in tooltips. They're for supplementary hints only. Critical content should be visible by default or in the main UI.