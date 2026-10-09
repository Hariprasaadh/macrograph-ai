import React, { useState, useMemo } from 'react';
import { TrendingUp, Calendar, Info } from 'lucide-react';

export interface TimeSeriesDataPoint {
  period: string;
  value: number;
  secondaryValue?: number;
  label?: string;
}

interface TimeSeriesChartProps {
  title: string;
  subtitle?: string;
  data: TimeSeriesDataPoint[];
  valuePrefix?: string;
  valueSuffix?: string;
  secondaryLabel?: string;
  secondarySuffix?: string;
  color?: 'emerald' | 'cyan' | 'indigo' | 'amber';
  height?: number;
  onInspectEvidence?: () => void;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  title,
  subtitle,
  data,
  valuePrefix = '',
  valueSuffix = '',
  secondaryLabel,
  secondarySuffix = '%',
  color = 'emerald',
  height = 220,
  onInspectEvidence,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [timeRange, setTimeRange] = useState<'3M' | '6M' | '1Y' | 'ALL'>('ALL');

  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];
    if (timeRange === '3M') return data.slice(-3);
    if (timeRange === '6M') return data.slice(-6);
    if (timeRange === '1Y') return data.slice(-12);
    return data;
  }, [data, timeRange]);

  const colorThemes = {
    emerald: {
      stroke: '#00e599',
      fillStart: 'rgba(0, 229, 153, 0.28)',
      fillEnd: 'rgba(0, 229, 153, 0.0)',
      accent: 'text-emerald-400',
      border: 'border-emerald-500/30',
      badge: 'bg-emerald-500/10 text-emerald-400',
    },
    cyan: {
      stroke: '#00c9ff',
      fillStart: 'rgba(0, 201, 255, 0.28)',
      fillEnd: 'rgba(0, 201, 255, 0.0)',
      accent: 'text-cyan-400',
      border: 'border-cyan-500/30',
      badge: 'bg-cyan-500/10 text-cyan-400',
    },
    indigo: {
      stroke: '#818cf8',
      fillStart: 'rgba(129, 140, 248, 0.28)',
      fillEnd: 'rgba(129, 140, 248, 0.0)',
      accent: 'text-indigo-400',
      border: 'border-indigo-500/30',
      badge: 'bg-indigo-500/10 text-indigo-400',
    },
    amber: {
      stroke: '#f59e0b',
      fillStart: 'rgba(245, 158, 11, 0.28)',
      fillEnd: 'rgba(245, 158, 11, 0.0)',
      accent: 'text-amber-400',
      border: 'border-amber-500/30',
      badge: 'bg-amber-500/10 text-amber-400',
    },
  };

  const theme = colorThemes[color];

  // SVG dimensions & scales
  const paddingX = 40;
  const paddingY = 24;
  const svgWidth = 600;
  const svgHeight = height;

  const { points, pathD, areaD } = useMemo(() => {
    if (filteredData.length === 0) {
      return { points: [], pathD: '', areaD: '' };
    }

    const values = filteredData.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const plotWidth = svgWidth - paddingX * 2;
    const plotHeight = svgHeight - paddingY * 2;

    const pts = filteredData.map((d, i) => {
      const x = paddingX + (i / Math.max(1, filteredData.length - 1)) * plotWidth;
      const normalizedY = (d.value - min) / range;
      const y = svgHeight - paddingY - normalizedY * plotHeight;
      return { x, y, data: d };
    });

    // Build smooth cubic bezier curve
    let pD = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const curr = pts[i];
      const next = pts[i + 1];
      const cx1 = curr.x + (next.x - curr.x) / 2;
      const cy1 = curr.y;
      const cx2 = curr.x + (next.x - curr.x) / 2;
      const cy2 = next.y;
      pD += ` C ${cx1} ${cy1}, ${cx2} ${cy2}, ${next.x} ${next.y}`;
    }

    const aD = `${pD} L ${pts[pts.length - 1].x} ${svgHeight - paddingY} L ${pts[0].x} ${svgHeight - paddingY} Z`;

    return { points: pts, minVal: min, maxVal: max, pathD: pD, areaD: aD };
  }, [filteredData, svgHeight, svgWidth]);

  const activePoint = hoverIndex !== null && points[hoverIndex] ? points[hoverIndex] : points[points.length - 1];

  return (
    <div className="p-5 rounded-2xl glass-panel border border-white/10 flex flex-col justify-between space-y-4 shadow-xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-1.5">
              <TrendingUp className={`w-4 h-4 ${theme.accent}`} />
              <span>{title}</span>
            </h3>
            {onInspectEvidence && (
              <button
                onClick={onInspectEvidence}
                title="Inspect DBIE provenance"
                className="text-slate-400 hover:text-white transition-colors"
                aria-label="Inspect evidence"
              >
                <Info className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>

        {/* Range Buttons */}
        <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-white/5 self-start sm:self-auto">
          {(['3M', '6M', '1Y', 'ALL'] as const).map((r) => (
            <button
              key={r}
              onClick={() => {
                setTimeRange(r);
                setHoverIndex(null);
              }}
              className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-all ${
                timeRange === r
                  ? 'bg-slate-800 text-white font-bold shadow-sm border border-white/10'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Main Active Metric Display */}
      {activePoint && (
        <div className="flex items-baseline justify-between border-b border-white/5 pb-2">
          <div>
            <div className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight">
              {valuePrefix}
              {typeof activePoint.data.value === 'number'
                ? activePoint.data.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                : activePoint.data.value}
              {valueSuffix}
            </div>
            {secondaryLabel && activePoint.data.secondaryValue !== undefined && (
              <div className="text-xs font-mono mt-0.5 text-slate-400 flex items-center gap-1.5">
                <span>{secondaryLabel}:</span>
                <span className={`font-semibold ${theme.accent}`}>
                  {activePoint.data.secondaryValue > 0 ? '+' : ''}
                  {activePoint.data.secondaryValue}
                  {secondarySuffix}
                </span>
              </div>
            )}
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
              <Calendar className="w-3 h-3 text-slate-500" />
              {activePoint.data.period}
            </span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full mt-1 inline-block border ${theme.badge}`}>
              Verified Data
            </span>
          </div>
        </div>
      )}

      {/* Interactive SVG Chart */}
      <div className="relative w-full overflow-hidden select-none" style={{ height }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-full overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={theme.stroke} stopOpacity="0.3" />
              <stop offset="100%" stopColor={theme.stroke} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={paddingX}
            y1={paddingY}
            x2={svgWidth - paddingX}
            y2={paddingY}
            stroke="rgba(255, 255, 255, 0.05)"
            strokeDasharray="3 3"
          />
          <line
            x1={paddingX}
            y1={svgHeight / 2}
            x2={svgWidth - paddingX}
            y2={svgHeight / 2}
            stroke="rgba(255, 255, 255, 0.05)"
            strokeDasharray="3 3"
          />
          <line
            x1={paddingX}
            y1={svgHeight - paddingY}
            x2={svgWidth - paddingX}
            y2={svgHeight - paddingY}
            stroke="rgba(255, 255, 255, 0.08)"
          />

          {/* Fill Area */}
          {areaD && <path d={areaD} fill={`url(#gradient-${color})`} />}

          {/* Stroke Line */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke={theme.stroke}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Crosshair on Hover */}
          {activePoint && (
            <g>
              <line
                x1={activePoint.x}
                y1={paddingY}
                x2={activePoint.x}
                y2={svgHeight - paddingY}
                stroke="rgba(255, 255, 255, 0.25)"
                strokeDasharray="2 2"
              />
              <circle
                cx={activePoint.x}
                cy={activePoint.y}
                r="5"
                fill="#040814"
                stroke={theme.stroke}
                strokeWidth="2.5"
              />
            </g>
          )}

          {/* Invisible interactive hover columns */}
          {points.map((pt, idx) => (
            <rect
              key={idx}
              x={pt.x - 15}
              y={0}
              width={30}
              height={svgHeight}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHoverIndex(idx)}
              onTouchStart={() => setHoverIndex(idx)}
            />
          ))}
        </svg>

        {/* X-axis labels */}
        <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1 px-4">
          <span>{filteredData[0]?.period ?? ''}</span>
          {filteredData.length > 2 && (
            <span>{filteredData[Math.floor(filteredData.length / 2)]?.period ?? ''}</span>
          )}
          <span>{filteredData[filteredData.length - 1]?.period ?? ''}</span>
        </div>
      </div>
    </div>
  );
};
