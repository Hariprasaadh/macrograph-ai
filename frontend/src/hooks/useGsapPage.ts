import { useEffect, useRef } from 'react';
import { ensureGsapRegistered, gsap, prefersReducedMotion, ScrollTrigger } from '../motion/gsapSetup';

/**
 * Page-level GSAP orchestration (UI-only).
 * - Entrance timeline: hero title / sub / cta stagger with expo.out
 * - Scroll batch: every `.reveal-gsap` fades up once via ScrollTrigger.batch
 * - Parallax: every `[data-parallax-speed]` drifts with scrub (background layers only)
 * All scoped with gsap.context and reverted on unmount. No data logic.
 */
export function useGsapPage(scopeRef: React.RefObject<HTMLElement>, deps: unknown[] = []): void {
  const depsKey = JSON.stringify(deps);
  useEffect(() => {
    const root = scopeRef.current;
    if (!root) return;
    ensureGsapRegistered();
    if (prefersReducedMotion()) {
      root.querySelectorAll('.reveal-gsap').forEach((el) => {
        (el as HTMLElement).style.opacity = '1';
      });
      return;
    }

    const ctx = gsap.context(() => {
      const entrance = root.querySelectorAll('[data-entrance]');
      if (entrance.length > 0) {
        gsap.fromTo(
          entrance,
          { y: 28, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.7, ease: 'expo.out', stagger: 0.09, overwrite: 'auto' }
        );
      }

      const batchTargets = gsap.utils.toArray<HTMLElement>('.reveal-gsap', root);
      if (batchTargets.length > 0) {
        gsap.set(batchTargets, { y: 22, opacity: 0 });
        ScrollTrigger.batch(batchTargets, {
          start: 'top 88%',
          once: true,
          onEnter: (els) =>
            gsap.to(els, { y: 0, opacity: 1, duration: 0.65, ease: 'expo.out', stagger: 0.08, overwrite: 'auto' }),
        });
      }

      gsap.utils.toArray<HTMLElement>('[data-parallax-speed]', root).forEach((layer) => {
        const speed = Number(layer.dataset.parallaxSpeed ?? '0');
        if (!Number.isFinite(speed) || speed === 0) return;
        gsap.to(layer, {
          yPercent: speed,
          ease: 'none',
          scrollTrigger: { trigger: layer.parentElement ?? layer, start: 'top bottom', end: 'bottom top', scrub: 0.6 },
        });
      });
    }, root);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeRef, depsKey]);
}

export function useScrollProgress(barRef: React.RefObject<HTMLDivElement>): void {
  const active = useRef(false);
  useEffect(() => {
    const bar = barRef.current;
    if (!bar || active.current) return;
    active.current = true;
    ensureGsapRegistered();
    if (prefersReducedMotion()) {
      bar.style.transform = 'scaleX(1)';
      return;
    }
    const tween = gsap.fromTo(
      bar,
      { scaleX: 0 },
      {
        scaleX: 1,
        ease: 'none',
        transformOrigin: '0 50%',
        scrollTrigger: { trigger: document.body, start: 'top top', end: 'bottom bottom', scrub: 0.3 },
      }
    );
    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
      active.current = false;
    };
  }, [barRef]);
}
