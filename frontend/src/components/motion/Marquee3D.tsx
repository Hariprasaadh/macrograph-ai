import React from 'react';

interface Marquee3DProps {
  items: string[];
  label?: string;
}

/**
 * Dual-row 3D marquee (UI-only). Two counter-scrolling rows inside a
 * perspective stage — Aceternity-style 3D Marquee built on the existing
 * transform-only marquee keyframes. Duplicated lists keep the loop seamless.
 */
export const Marquee3D: React.FC<Marquee3DProps> = ({ items, label = 'Trusted data authorities' }) => {
  const row = [...items, ...items];
  return (
    <div aria-label={label} className="marquee-3d-stage mx-auto mt-12 max-w-5xl">
      <p className="mesh-eyebrow mb-3 text-slate-500">_Trusted by official authorities_</p>
      <div className="marquee-3d-viewport overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.02] backdrop-blur-xl">
        <div className="mesh-marquee-track gap-3 px-4 py-3.5" aria-hidden="true">
          {row.map((t, i) => (
            <span
              key={`a-${i}`}
              className="shrink-0 whitespace-nowrap rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 font-mono text-xs text-slate-300"
            >
              {t}
            </span>
          ))}
        </div>
        <div className="mesh-marquee-track mesh-marquee-reverse gap-3 border-t border-white/[0.06] px-4 py-3.5" aria-hidden="true">
          {row.map((t, i) => (
            <span
              key={`b-${i}`}
              className="shrink-0 whitespace-nowrap rounded-full border border-cyan-400/15 bg-cyan-400/[0.04] px-4 py-1.5 font-mono text-xs text-cyan-200/80"
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
