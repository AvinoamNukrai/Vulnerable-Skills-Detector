# Use transform and opacity for animations

> Animate with CSS transform and opacity properties to keep animations running on the GPU compositor thread at 60fps, avoiding layout-triggering properties like top, left, width, and height.

**Priority:** high · **Difficulty:** intermediate · **Time:** 20 min

---
The browser renders pages through a pipeline: Style → Layout → Paint → Composite. Animating the wrong properties restarts this pipeline every frame. Animating `transform` and `opacity` only triggers the composite step.

## Code Example

```
Layout-triggering properties (avoid animating):
  width, height, margin, padding, top, left, right, bottom,
  border-width, font-size, display, position

Paint-triggering properties (acceptable, but not ideal):
  color, background-color, box-shadow, border-color,
  outline, text-shadow

Compositor-only properties (optimal for animation):
  transform (translate, scale, rotate, skew)
  opacity
  filter (on composited layers)
```

## Why It Matters

Animating layout properties (width, height, top, margin) triggers the full browser rendering pipeline on every frame — style recalculation, layout, paint, and composite. This runs on the main thread and competes with JavaScript. Animating transform and opacity skips layout and paint entirely and runs on a dedicated GPU thread, achieving smooth 60fps even when the main thread is busy.

## Converting Position Animations

```css
/* ❌ Bad: animates layout properties — triggers full reflow each frame */
.slide-in {
  animation: slideIn 300ms ease-out;
}

@keyframes slideIn {
  from { left: -100%; }
  to { left: 0; }
}

/* ✅ Good: translate() is compositor-only */
.slide-in {
  animation: slideIn 300ms ease-out;
}

@keyframes slideIn {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}
```

## Converting Size Animations

```css
/* ❌ Animates width/height — expensive */
.expand {
  animation: expand 300ms ease;
}
@keyframes expand {
  from { width: 0; height: 0; }
  to { width: 200px; height: 200px; }
}

/* ✅ Use scale() */
.expand {
  width: 200px;
  height: 200px;
  animation: expand 300ms ease;
}
@keyframes expand {
  from { transform: scale(0); }
  to { transform: scale(1); }
}
```

## Common Performant Patterns

```css
/* Fade in */
.fade-in {
  animation: fadeIn 300ms ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Slide up and fade in */
.slide-up {
  animation: slideUp 400ms cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Button press */
.button:active {
  transform: scale(0.97);
}
```

## will-change (Use Sparingly)

```css
/* Hint to browser to promote this element to its own layer before animation starts */
.animated-card {
  will-change: transform;
}

/* ⚠️ Don't apply to too many elements — each layer uses GPU memory */
/* Apply just before animation, remove after */
```

## Respecting Reduced Motion

```css
/* ✅ Always honor the user's motion preferences */
.slide-in {
  animation: slideIn 400ms ease;
}

@media (prefers-reduced-motion: reduce) {
  .slide-in {
    animation: none;
    /* Provide a non-animated alternative if needed */
  }
}

/* Or use the safe pattern */
@media (prefers-reduced-motion: no-preference) {
  .slide-in {
    animation: slideIn 400ms ease;
  }
}
```

## Verification

1. Inspect the rendered UI at the breakpoints and interaction states affected by the rule.
2. Confirm the computed styles match the intended fix in DevTools.
3. Test at least one mobile and one desktop viewport before shipping.
4. If the rule affects motion, contrast, or layout stability, verify those user-facing outcomes directly.