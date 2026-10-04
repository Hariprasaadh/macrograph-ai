import React from 'react';

/**
 * Multi-layer parallax hero backdrop (UI-only, decorative).
 * Three depth layers drift at independent speeds via `data-parallax-speed`
 * consumed by useGsapPage (ScrollTrigger scrub). Foreground content is
 * never parallaxed — only ambient glows/grid. Pointer-events none.
 */
export const ParallaxHero: React.FC = () => {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div data-parallax-speed="-12" className="parallax-layer absolute inset-0">
        <div className="absolute left-1/2 top-0 h-[650px] w-[1200px] -translate-x-1/2 bg-radial-gradient" />
        <div className="bg-grid-pattern absolute inset-0 opacity-70 [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black,transparent)]" />
      </div>
      <div data-parallax-speed="10" className="parallax-layer absolute inset-0">
        <div className="absolute right-[-15%] top-40 h-[600px] w-[600px] rounded-full bg-brand-500/10 blur-[150px]" />
        <div className="absolute left-[-15%] top-96 h-[600px] w-[600px] rounded-full bg-accent-cyan/10 blur-[150px]" />
      </div>
      <div data-parallax-speed="18" className="parallax-layer absolute inset-0">
        <div className="absolute bottom-10 right-1/4 h-[500px] w-[500px] rounded-full bg-purple-600/10 blur-[160px]" />
        <div className="float-weightless absolute left-[12%] top-[22%] h-24 w-24 rounded-3xl border border-cyan-400/20 bg-cyan-400/5 backdrop-blur-xl" />
        <div className="float-weightless absolute right-[10%] top-[30%] h-16 w-16 rounded-2xl border border-brand-400/20 bg-brand-400/5 backdrop-blur-xl [animation-delay:-3s]" />
      </div>
    </div>
  );
};
