# GSAP SVG Plugins

Read before animating inline SVG strokes, morphs, or motion paths.

## Registration

```js
import gsap from 'gsap';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';
import { MorphSVGPlugin } from 'gsap/MorphSVGPlugin';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(DrawSVGPlugin, MorphSVGPlugin, MotionPathPlugin, ScrollTrigger);
```

## DrawSVG — stroke reveal

**Prerequisite:** path must have `stroke` and `stroke-width` (CSS or attribute).

```js
// Draw from hidden to full stroke
gsap.from('.draw-me', { duration: 1.5, drawSVG: 0, stagger: 0.1 });

// Draw a segment that travels along the path
gsap.fromTo(path, { drawSVG: '0% 5%' }, { duration: 2, drawSVG: '95% 100%' });

// Responsive path length changes
gsap.to(path, { drawSVG: '0% 100% live', duration: 1 });
```

**Caveats:**
- Stroke only — no fill animation.
- Multi-segment `<path>` (multiple `M` commands) renders poorly — split into separate paths.
- `drawSVG: "100%"` equals `"0% 100%"` — value is end state, not a range to tween through.

## MorphSVG — shape transitions

Paths need compatible point structure. When authoring, use `svg-creation` morph rules (same command count/types).

```js
gsap.to('#icon-path', {
  duration: 0.4,
  morphSVG: '#icon-path-close',
  ease: 'power2.inOut',
});
```

Or morph to a raw path string:

```js
gsap.to('#hamburger', { morphSVG: 'M5,5 L19,19 M5,19 L19,5', duration: 0.35 });
```

## MotionPath — travel along curve

```js
gsap.to('.dot', {
  duration: 3,
  repeat: -1,
  ease: 'none',
  motionPath: {
    path: '#orbit-path',
    align: '#orbit-path',
    autoRotate: true,
  },
});
```

`path` can be an SVG path element, selector, or SVG path data string.

## ScrollTrigger — scroll-driven SVG/DOM

```js
gsap.from('.section-svg', {
  drawSVG: 0,
  scrollTrigger: {
    trigger: '.section-svg',
    start: 'top 80%',
    end: 'top 20%',
    scrub: 1,
  },
});
```

Pin + scrub for sticky diagram build:

```js
ScrollTrigger.create({
  trigger: '.diagram-wrap',
  start: 'top top',
  end: '+=800',
  pin: true,
  scrub: true,
  animation: tl, // timeline of draw steps
});
```

Kill on teardown: `ScrollTrigger.getAll().forEach(t => t.kill())` inside context revert (automatic with `useGSAP`).

## Performance notes

- Prefer `transform` / `opacity` on groups (`<g>`) over morphing complex `d` every frame.
- Stagger many paths with `timeline` + small `stagger` (0.05–0.12) instead of one long tween.
- For heroes only: animating `filter` or large `d` — acceptable; avoid on lists.

## When NOT to use plugins

| Need | Use instead |
|------|-------------|
| README-embeddable animated SVG | `svg-creation` SMIL |
| Single CSS hover on inline SVG | CSS `transition` |
| React list enter/exit without scroll | Motion (`motion-animation`) |
