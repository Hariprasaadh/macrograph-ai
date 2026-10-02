# GSAP Animation — Worked Examples

Read when the animation pattern or output shape is unclear.

---

## Example 1 — SVG logo draw on load (React)

**Input:** Animate an inline SVG logo path draw on page load in React.

**Output:**

```tsx
'use client';
import { useRef } from 'react';
import gsap from 'gsap';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(DrawSVGPlugin, useGSAP);

export function LogoDraw() {
  const root = useRef<SVGSVGElement>(null);
  useGSAP(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.from(root.current!.querySelectorAll('.stroke'), {
      duration: 1.2, drawSVG: 0, stagger: 0.15, ease: 'power2.inOut',
    });
  }, { scope: root });
  return (
    <svg ref={root} viewBox="0 0 200 60" aria-hidden="true">
      <path className="stroke" fill="none" stroke="currentColor" strokeWidth="2"
        d="M10,30 L50,30 L70,10 L90,50 L110,30 L190,30"/>
    </svg>
  );
}
```

---

## Example 2 — Page-load timeline stagger (vanilla)

**Input:** Stagger hero headline, subcopy, and CTA on landing page load.

**Output:**

```html
<div id="hero">
  <h1 class="hero-line">Ship faster</h1>
  <p class="hero-line">Agents that remember.</p>
  <button class="hero-cta">Get started</button>
</div>
<script type="module">
import gsap from 'gsap';

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reduced) {
  const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });
  tl.from('.hero-line', { y: 32, opacity: 0, duration: 0.7, stagger: 0.1 })
    .from('.hero-cta', { y: 16, opacity: 0, duration: 0.45 }, '-=0.25');
}
</script>
```

Pattern: single timeline, negative overlap for natural rhythm.

---

## Example 3 — ScrollTrigger section reveal (React)

**Input:** Fade and slide up feature cards as user scrolls.

**Output:**

```tsx
'use client';
import { useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(ScrollTrigger, useGSAP);

export function FeatureGrid({ items }: { items: string[] }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.from('.feature-card', {
      y: 48, opacity: 0, duration: 0.6, stagger: 0.12,
      scrollTrigger: { trigger: root.current, start: 'top 75%' },
    });
  }, { scope: root });
  return (
    <div ref={root} className="grid">
      {items.map((t) => <article key={t} className="feature-card">{t}</article>)}
    </div>
  );
}
```

ScrollTrigger auto-cleaned via `useGSAP` context on unmount.

---

## Example 4 — SVG morph toggle (inline DOM)

**Input:** Hamburger icon morphs to X on menu open — must run in SPA, not standalone SVG file.

**Output:**

```tsx
'use client';
import { useRef } from 'react';
import gsap from 'gsap';
import { MorphSVGPlugin } from 'gsap/MorphSVGPlugin';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(MorphSVGPlugin, useGSAP);

const OPEN = 'M6,6 L18,18 M6,18 L18,6';
const CLOSED = 'M4,7 L20,7 M4,12 L20,12 M4,17 L20,17';

export function MenuIcon({ open }: { open: boolean }) {
  const path = useRef<SVGPathElement>(null);
  useGSAP(() => {
    gsap.to(path.current, {
      duration: 0.35, morphSVG: open ? OPEN : CLOSED, ease: 'power2.inOut',
    });
  }, { dependencies: [open] });
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
      <path ref={path} stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" fill="none" d={CLOSED}/>
    </svg>
  );
}
```

For README-embeddable morph without JS → `svg-creation` SMIL example 3.

---

## Example 5 — DrawSVG diagram build on scroll

**Input:** Architecture diagram paths draw in sequence as user scrolls through pinned section.

**Output:**

```js
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: '.diagram',
    start: 'top top',
    end: '+=1200',
    pin: true,
    scrub: 1,
  },
});
tl.from('.wire', { drawSVG: 0, duration: 1, stagger: 0.2 });
```

Each `.wire` path needs `stroke` + `stroke-width`. Split multi-segment paths before animating.
