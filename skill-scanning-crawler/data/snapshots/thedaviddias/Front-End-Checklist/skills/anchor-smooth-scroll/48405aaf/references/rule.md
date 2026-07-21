# Provide instant anchor scroll option

> Smooth scroll animations to anchor links respect motion preferences or provide an instant alternative.

**Priority:** low · **Difficulty:** beginner · **Time:** 10 min

---
Smooth scrolling should respect motion preferences to avoid triggering vestibular disorders.

## Code Example

```css
/* ❌ Bad: Always smooth, ignores preferences */
html {
  scroll-behavior: smooth;
}

/* ✅ Good: Respect motion preferences */
@media (prefers-reduced-motion: no-preference) {
  html {
    scroll-behavior: smooth;
  }
}

/* Users who prefer reduced motion get instant scrolling (default) */
```

## Why It Matters

Smooth scroll animations can trigger vertigo, nausea, and disorientation for users with vestibular disorders—instant navigation is safer and often faster.

## JavaScript Approach

```typescript
function scrollToElement(elementId: string) {
  const element = document.getElementById(elementId)
  if (!element) return

  const prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches

  element.scrollIntoView({
    behavior: prefersReducedMotion ? 'instant' : 'smooth',
    block: 'start'
  })

  // Move focus to target for keyboard users
  element.focus({ preventScroll: true })
}
```

## React Hook

```tsx
function useScrollToAnchor() {
  const prefersReducedMotion = useReducedMotion()

  const scrollTo = useCallback((elementId: string) => {
    const element = document.getElementById(elementId)
    if (!element) return

    element.scrollIntoView({
      behavior: prefersReducedMotion ? 'instant' : 'smooth',
      block: 'start'
    })

    // Set tabindex if element isn't focusable
    if (!element.hasAttribute('tabindex')) {
      element.setAttribute('tabindex', '-1')
    }
    element.focus({ preventScroll: true })
  }, [prefersReducedMotion])

  return scrollTo
}

function useReducedMotion() {
  const [prefersReduced, setPrefersReduced] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReduced(mediaQuery.matches)

    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  return prefersReduced
}
```

## Anchor Link Component

```tsx
interface AnchorLinkProps {
  href: string
  children: React.ReactNode
}

function AnchorLink({ href, children }: AnchorLinkProps) {
  const scrollTo = useScrollToAnchor()

  const handleClick = (e: React.MouseEvent) => {
    if (href.startsWith('#')) {
      e.preventDefault()
      scrollTo(href.slice(1))
    }
  }

  return (
    <a href={href} onClick={handleClick}>
      {children}
    </a>
  )
}
```

## Focus Management

```html
<!-- Target must be focusable for keyboard navigation -->
<section id="features" tabindex="-1">
  <h2>Features</h2>
  <!-- Content -->
</section>
```

```css
/* Hide focus ring when section is focused via anchor */
section:focus {
  outline: none;
}

/* But show focus for keyboard navigation */
section:focus-visible {
  outline: 2px solid var(--focus-color);
}
```

## Exceptions

- Simple data tables can sometimes fail more from missing header relationships than from missing enhancements such as captions or mobile wrappers, so prioritize the strongest semantic issue.
- Do not convert layout structures into data-table markup just to satisfy a rule; the correct fix may be to remove table semantics entirely.
- When several table-accessibility issues overlap, resolve the header-cell relationship first because downstream announcements depend on it.

## Verification

### Automated Checks

- Use browser accessibility tooling, axe, Lighthouse, or equivalent automated checks against a representative rendered state.

### Manual Checks

- Enable "Reduce motion" in system accessibility settings
- Click anchor links—should scroll instantly, not smoothly
- Verify focus moves to target section
- Tab through page after anchor click—focus should continue from anchor target