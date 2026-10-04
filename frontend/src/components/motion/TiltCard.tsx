import React, { useCallback, useRef } from 'react';
import { prefersReducedMotion } from '../../motion/gsapSetup';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;
  glare?: boolean;
  label?: string;
}

/**
 * Aceternity-style 3D Card Effect (UI-only wrapper).
 * Mouse-tracked perspective tilt + moving glare. Transform/opacity only,
 * rAF-throttled, reduced-motion safe. Never touches data or backend calls.
 */
export const TiltCard: React.FC<TiltCardProps> = ({
  children,
  className = '',
  maxTilt = 7,
  glare = true,
  label,
}) => {
  const frameRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  const setTilt = useCallback(
    (rx: number, ry: number, glareX: number, glareY: number, scale: number) => {
      const el = frameRef.current;
      if (!el) return;
      el.style.transform = `perspective(1100px) rotateX(${rx}deg) rotateY(${ry}deg) scale3d(${scale}, ${scale}, 1)`;
      el.style.setProperty('--tilt-glare-x', `${glareX}%`);
      el.style.setProperty('--tilt-glare-y', `${glareY}%`);
    },
    []
  );

  const handleMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (prefersReducedMotion()) return;
      const el = frameRef.current;
      if (!el) return;
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const px = (e.clientX - rect.left) / Math.max(rect.width, 1);
        const py = (e.clientY - rect.top) / Math.max(rect.height, 1);
        const ry = (px - 0.5) * maxTilt * 2;
        const rx = (0.5 - py) * maxTilt * 2;
        setTilt(rx, ry, px * 100, py * 100, 1.015);
      });
    },
    [maxTilt, setTilt]
  );

  const handleLeave = useCallback(() => {
    if (prefersReducedMotion()) return;
    cancelAnimationFrame(rafRef.current);
    const el = frameRef.current;
    if (!el) return;
    el.style.transition = 'transform 0.55s cubic-bezier(0.16, 1, 0.3, 1)';
    setTilt(0, 0, 50, 50, 1);
    window.setTimeout(() => {
      if (frameRef.current) frameRef.current.style.transition = '';
    }, 560);
  }, [setTilt]);

  return (
    <div className={`tilt-scene ${className}`} aria-label={label}>
      <div
        ref={frameRef}
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        className="tilt-inner h-full w-full will-change-transform"
      >
        {children}
        {glare && <span aria-hidden="true" className="tilt-glare" />}
      </div>
    </div>
  );
};
