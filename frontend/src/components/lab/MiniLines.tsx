import React from 'react';

export interface MiniSeries {
  label: string;
  color: string;
  dashed?: boolean;
  points: Array<{ t: number; value: number }>;
}

interface MiniLinesProps {
  series: MiniSeries[];
  /** vertical marker, e.g. the current month of the animation */
  cursor?: number | null;
  height?: number;
  xLabel?: string;
}

/** Tiny multi-line SVG chart. Each series is normalised to its own range so unlike units are comparable. */
export const MiniLines: React.FC<MiniLinesProps> = ({ series, cursor = null, height = 170, xLabel = 'months' }) => {
  const width = 560;
  const pad = 28;
  const maxT = Math.max(1, ...series.flatMap((s) => s.points.map((p) => p.t)));
  const x = (t: number) => pad + (t / maxT) * (width - pad * 2);
  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="rgba(255,255,255,0.12)" />
        {series.map((s) => {
          const values = s.points.map((p) => p.value);
          const min = Math.min(...values);
          const max = Math.max(...values);
          const range = max - min || 1;
          const y = (v: number) => height - pad - ((v - min) / range) * (height - pad * 2) * (max === min ? 0 : 1) - (max === min ? (height - pad * 2) / 2 : 0);
          const d = s.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.t)} ${y(p.value)}`).join(' ');
          return <path key={s.label} d={d} fill="none" stroke={s.color} strokeWidth="2.2" strokeDasharray={s.dashed ? '5 4' : undefined} strokeLinejoin="round" />;
        })}
        {cursor !== null && <line x1={x(cursor)} y1={pad / 2} x2={x(cursor)} y2={height - pad} stroke="rgba(255,255,255,0.4)" strokeDasharray="3 3" />}
        <text x={pad} y={height - 8} fontSize="10" fill="#64748b" fontFamily="monospace">0</text>
        <text x={width - pad} y={height - 8} fontSize="10" fill="#64748b" fontFamily="monospace" textAnchor="end">{maxT} {xLabel}</text>
      </svg>
      <div className="flex flex-wrap gap-3 mt-1 text-[10px] font-mono text-slate-400">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: s.color }} />{s.label}
          </span>
        ))}
      </div>
    </div>
  );
};
