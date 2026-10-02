# GSAP React Integration

Read when the stack is React, Next.js, or Remix with client components.

## Install

```bash
npm install gsap @gsap/react
```

## Basic pattern

```tsx
'use client';
import { useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

export function AnimatedBlock() {
  const container = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    gsap.from('.reveal', { y: 24, opacity: 0, duration: 0.6, stagger: 0.08 });
  }, { scope: container });

  return (
    <div ref={container}>
      <p className="reveal">One</p>
      <p className="reveal">Two</p>
    </div>
  );
}
```

`useGSAP` wraps `gsap.context()` — all tweens created during the callback revert on unmount.

## Config object

```js
useGSAP(() => { /* tweens */ }, {
  scope: container,           // limit selector text to descendants
  dependencies: [activeTab],  // re-run when deps change
  revertOnUpdate: true,       // revert + re-run on dep change (not just unmount)
});
```

## Interaction handlers (context-safe)

Animations in `onClick` run **after** mount — not auto-recorded unless wrapped:

```tsx
const container = useRef(null);
const { contextSafe } = useGSAP({ scope: container });

const onClick = contextSafe(() => {
  gsap.to('.toggle', { rotation: 180, duration: 0.3 });
});
```

Inside `useGSAP` callback, use the second argument:

```js
useGSAP((ctx, contextSafe) => {
  const handler = contextSafe(() => gsap.to(el, { scale: 1.05 }));
  el.addEventListener('click', handler);
  return () => el.removeEventListener('click', handler);
}, { scope: container });
```

## Next.js App Router

- Add `'use client'` at file top.
- `useGSAP` is SSR-safe (uses `useLayoutEffect` when `window` exists).
- Lazy-load heavy animation components with `dynamic(() => import(...), { ssr: false })` only when they touch `window` before hydration — not required for standard `useGSAP`.

## Vue / Svelte / vanilla

Use manual context:

```js
let ctx;
onMounted(() => {
  ctx = gsap.context(() => {
    gsap.to('.box', { x: 100 });
  }, rootEl);
});
onUnmounted(() => ctx?.revert());
```

## Timeline in React

```js
useGSAP(() => {
  const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });
  tl.from('.hero-title', { y: 40, opacity: 0, duration: 0.7 })
    .from('.hero-sub', { y: 20, opacity: 0, duration: 0.5 }, '-=0.3')
    .from('.hero-cta', { scale: 0.9, opacity: 0, duration: 0.4 }, '-=0.2');
}, { scope: container });
```

Return cleanup only for manual listeners — timeline is reverted by context.
