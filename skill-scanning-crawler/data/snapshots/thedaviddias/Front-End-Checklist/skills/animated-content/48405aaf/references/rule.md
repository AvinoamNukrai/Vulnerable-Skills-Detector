# Convert animated GIFs to video

> Large animated GIFs are replaced with more efficient video formats like MP4 or WebM to reduce page weight.

**Priority:** medium · **Difficulty:** intermediate · **Time:** 10 min

---
Large animated GIFs are often used for short animations, but they are highly inefficient compared to modern video formats. Converting these to MP4 or WebM can reduce file sizes by 80% or more.

## Code Examples

#

## Traditional GIF (Inefficient)
```html
<img src="animation.gif" alt="Description of animation">
```

### Optimized Video (Recommended)
Using the `<video>` tag with specific attributes to mimic GIF behavior:

```html
<video
  autoplay
  loop
  muted
  playsinline
  poster="animation-frame.jpg"
>
  <source src="animation.webm" type="video/webm">
  <source src="animation.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
```

## Why It Matters

- **Page Weight**: GIFs are uncompressed and can easily reach several megabytes, slowing down page loads.
- **CPU Usage**: Browsers consume more CPU/GPU resources to decode and render large GIFs compared to optimized video.
- **Battery Life**: On mobile devices, the high resource usage of GIFs can significantly drain battery.
- **User Experience**: Large assets delay the completion of page loading and can cause stuttering during scrolling.

## Best Practices

Favor [browser-native video delivery guidance from web.dev](https://web.dev/learn/performance) when deciding whether an animation should stay a GIF at all, because the biggest wins usually come from eliminating heavy animated assets rather than just caching them better.

✅ **Use Modern Formats**: Provide WebM for modern browsers and MP4 as a fallback.
✅ **Add Poster Images**: Use the `poster` attribute to show a static frame while the video loads.
✅ **Mute by Default**: Always use `muted` for autoplaying videos to ensure they work across all browsers.
✅ **Lazy Loading**: Use `loading="lazy"` or Intersection Observer for videos below the fold.

❌ **Avoid GIF for Large Animations**: Never use GIF for animations larger than a few hundred pixels or longer than a second.
❌ **Don't Forget Accessibility**: Always provide alternative text or a description for the animation.

## Tools & Validation

- [FFmpeg](https://ffmpeg.org/): Command-line tool for converting GIFs to video.
- [Cloudinary/Imgix](https://cloudinary.com/): Automated media optimization services.
- [Lighthouse](https://developers.google.com/web/tools/lighthouse): Checks for large GIFs and suggests video alternatives.

## Standards

- Use web.dev: Learn Performance as the standard for measuring the final production behavior, not just local synthetic output.
- Use Chrome Developers: Lighthouse overview as the standard for measuring the final production behavior, not just local synthetic output.

## Verification

### Automated Checks

- Measure the affected page or flow in Lighthouse, PageSpeed Insights, or DevTools and confirm the targeted metric improves.
- Inspect the network waterfall or performance timeline to confirm the intended resource or execution change actually took effect.

### Manual Checks

- Verify the change on a throttled mobile profile, not just local desktop.
- If this rule maps to a budget or Web Vital, confirm the page now stays within that threshold.