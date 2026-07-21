# Make notifications accessible

> Toast notifications and alerts are announced to screen readers using ARIA live regions and appropriate roles.

**Priority:** high · **Difficulty:** intermediate · **Time:** 25 min

---
Accessible notifications ensure all users receive important feedback about actions and state changes.

## Code Example

```html
<!-- Status notification (polite) -->
<div role="status" aria-live="polite" class="notification">
  Your changes have been saved.
</div>

<!-- Alert notification (assertive) -->
<div role="alert" aria-live="assertive" class="notification notification--error">
  Error: Please fill in all required fields.
</div>

<!-- Live region container (content injected dynamically) -->
<div
  id="notifications"
  aria-live="polite"
  aria-atomic="true"
  class="sr-only"
></div>
```

## Why It Matters

Without proper ARIA attributes, screen reader users miss critical notifications like form errors, success messages, and real-time updates—leaving them unaware of important page changes.

## ARIA Live Region Types

| Attribute | Behavior | Use For |
|-----------|----------|---------|
| `aria-live="polite"` | Waits for user pause | Status updates, non-urgent info |
| `aria-live="assertive"` | Interrupts immediately | Errors, time-sensitive alerts |
| `role="status"` | Implicit polite | Progress, success messages |
| `role="alert"` | Implicit assertive | Errors, warnings |

## React Toast Component

```tsx

type NotificationType = 'success' | 'error' | 'warning' | 'info'

interface ToastProps {
  message: string
  type: NotificationType
  duration?: number
  onDismiss: () => void
}

  message,
  type,
  duration = 5000,
  onDismiss
}: ToastProps) {
  const toastRef = useRef(null)

  // Auto-dismiss after duration
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onDismiss, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onDismiss])

  // Focus toast for keyboard users
  useEffect(() => {
    toastRef.current?.focus()
  }, [])

  const isError = type === 'error' || type === 'warning'

  return (
    <div
      ref={toastRef}
      role={isError ? 'alert' : 'status'}
      aria-live={isError ? 'assertive' : 'polite'}
      aria-atomic="true"
      tabIndex={-1}
      className={`toast toast--${type}`}
    >
      <span className="toast__icon" aria-hidden="true">
        {type === 'success' && '✓'}
        {type === 'error' && '✕'}
        {type === 'warning' && '⚠'}
        {type === 'info' && 'ℹ'}
      </span>

      <span className="toast__message">{message}</span>

      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="toast__dismiss"
      >
        ×
      </button>
    </div>
  )
}
```

## Toast Container with Live Region

```tsx

interface Notification {
  id: string
  message: string
  type: NotificationType
  duration?: number
}

interface ToastContextType {
  addToast: (notification: Omit
      {children}

      {/* Toast container with live region */}
      <div
        className="toast-container"
        aria-label="Notifications"
      >
        {toasts.map(toast => (
           removeToast(toast.id)}
          />
        ))}
      </div>

      {/* Screen reader announcement region */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {toasts.length > 0 && toasts[toasts.length - 1].message}
      </div>
    </ToastContext.Provider>
  )
}

  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
```

## Usage Example

```tsx
function SaveButton() {
  const { addToast } = useToast()

  const handleSave = async () => {
    try {
      await saveData()
      addToast({
        message: 'Changes saved successfully',
        type: 'success',
        duration: 3000
      })
    } catch (error) {
      addToast({
        message: 'Failed to save changes. Please try again.',
        type: 'error',
        duration: 0 // Don't auto-dismiss errors
      })
    }
  }

  return <button onClick={handleSave}>Save</button>
}
```

## Inline Notifications

```tsx
interface InlineNotificationProps {
  type: 'error' | 'warning' | 'success' | 'info'
  title?: string
  children: React.ReactNode
  dismissible?: boolean
  onDismiss?: () => void
}

  type,
  title,
  children,
  dismissible = false,
  onDismiss
}: InlineNotificationProps) {
  const isUrgent = type === 'error' || type === 'warning'

  return (
    <div
      role={isUrgent ? 'alert' : 'status'}
      aria-live={isUrgent ? 'assertive' : 'polite'}
      className={`notification notification--${type}`}
    >
      {title && (
        <strong className="notification__title">{title}</strong>
      )}
      <div className="notification__content">{children}</div>

      {dismissible && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="notification__dismiss"
        >
          ×
        </button>
      )}
    </div>
  )
}
```

## Progress Notifications

```tsx
function UploadProgress({ progress, fileName }: { progress: number; fileName: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy={progress < 100}
      className="upload-progress"
    >
      <span className="sr-only">
        Uploading {fileName}: {progress}% complete
      </span>

      <div aria-hidden="true">
        <span>{fileName}</span>
        <progress value={progress} max="100" />
        <span>{progress}%</span>
      </div>
    </div>
  )
}
```

## Timing Guidelines

| Notification Type | Recommended Duration |
|-------------------|---------------------|
| Success messages | 3-5 seconds |
| Info/status | 5-7 seconds |
| Warnings | 8-10 seconds or manual dismiss |
| Errors | No auto-dismiss (manual only) |

```tsx
const DURATION_MAP = {
  success: 3000,
  info: 5000,
  warning: 8000,
  error: 0, // No auto-dismiss
} as const
```

## Styling

```css
.toast-container {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: slideIn 0.3s ease-out;
}

.toast--success { background: #d4edda; border-left: 4px solid #28a745; }
.toast--error { background: #f8d7da; border-left: 4px solid #dc3545; }
.toast--warning { background: #fff3cd; border-left: 4px solid #ffc107; }
.toast--info { background: #d1ecf1; border-left: 4px solid #17a2b8; }

.toast__dismiss {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem;
  margin-left: auto;
}

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .toast {
    animation: none;
  }
}
```

## Verification

1. Enable screen reader and trigger notifications
2. Verify announcements occur at appropriate times
3. Test keyboard dismissal (Escape key)
4. Check notifications don't disappear too quickly
5. Verify focus management after dismissal
6. Test with different screen readers (NVDA, VoiceOver, JAWS)

Reserve `aria-live="assertive"` for truly urgent messages. Overuse disrupts the user experience by constantly interrupting screen reader output.