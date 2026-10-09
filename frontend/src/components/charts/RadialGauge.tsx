import React from 'react';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

interface RadialGaugeProps {
  title: string;
  value: number;
  max?: number;
  suffix?: string;
  target?: number;
  targetLabel?: string;
  subtext?: string;
  color?: 'emerald' | 'cyan' | 'indigo';
  size?: number;
}

export const RadialGauge: React.FC<RadialGaugeProps> = ({
  title,
  value,
  max = 25,
  suffix = '%',
  target = 11.5,
  targetLabel = 'Reg. Min',
  subtext,
  color = 'cyan',
  size = 140,
}) => {
  const strokeWidth = 10;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;

  // Percentage of circular arc (270 degrees arc)
  const arcLength = circumference * 0.75;
  const progressRatio = Math.min(1, Math.max(0, value / max));
  const strokeDashoffset = arcLength - progressRatio * arcLength;

  const targetRatio = Math.min(1, Math.max(0, target / max));
  const targetOffset = arcLength - targetRatio * arcLength;

  const colorStyles = {
    emerald: {
      stroke: '#00e599',
      glow: 'drop-shadow(0 0 10px rgba(0, 229, 153, 0.4))',
      text: 'text-emerald-400',
    },
    cyan: {
      stroke: '#00c9ff',
      glow: 'drop-shadow(0 0 10px rgba(0, 201, 255, 0.4))',
      text: 'text-cyan-400',
    },
    indigo: {
      stroke: '#818cf8',
      glow: 'drop-shadow(0 0 10px rgba(129, 140, 248, 0.4))',
      text: 'text-indigo-400',
    },
  };

  const currentTheme = colorStyles[color];

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col items-center justify-between text-center relative overflow-hidden group hover:border-white/15 transition-all">
      <div className="w-full flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
        <span className="truncate">{title}</span>
        <ShieldCheck className={`w-3.5 h-3.5 ${currentTheme.text}`} />
      </div>

      <div className="relative flex items-center justify-center my-1" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="transform -rotate-135 overflow-visible"
        >
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />

          {/* Value Progress Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke={currentTheme.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              filter: currentTheme.glow,
              transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          />

          {/* Target Milestone Marker */}
          {target && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="#f43f5e"
              strokeWidth={strokeWidth + 2}
              strokeDasharray={`2 ${circumference}`}
              strokeDashoffset={targetOffset}
              strokeLinecap="butt"
            />
          )}
        </svg>

        {/* Center Text Readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-extrabold text-white font-mono tracking-tight">
            {value.toFixed(1)}
            <span className="text-xs text-slate-400 font-normal ml-0.5">{suffix}</span>
          </span>
          {target && (
            <span className="text-[10px] text-slate-400 font-mono mt-0.5">
              {targetLabel}: {target}{suffix}
            </span>
          )}
        </div>
      </div>

      {subtext && (
        <div className="mt-2 text-[11px] text-slate-400 font-mono flex items-center gap-1.5 justify-center">
          <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
          <span>{subtext}</span>
        </div>
      )}
    </div>
  );
};
