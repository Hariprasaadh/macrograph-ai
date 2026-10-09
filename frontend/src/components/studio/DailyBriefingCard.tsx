import React from 'react';
import { Newspaper, Calendar, Sparkles, Compass } from 'lucide-react';
import { DailyBriefing } from '../../types';

interface DailyBriefingCardProps {
  briefing?: DailyBriefing | null;
}

export const DailyBriefingCard: React.FC<DailyBriefingCardProps> = ({ briefing }) => {
  if (!briefing) return null;

  return (
    <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-5 shadow-2xl relative overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Newspaper className="w-4 h-4" />
            </span>
            <span className="text-[11px] font-mono uppercase tracking-wider text-indigo-400 font-bold">
              Autonomous Intelligence Briefing
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              Verified Pipeline
            </span>
          </div>
          <h2 className="text-base sm:text-lg font-bold text-white mt-1.5 leading-snug tracking-tight">
            {briefing.headline}
          </h2>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-white/5 shrink-0">
          <Calendar className="w-3.5 h-3.5 text-indigo-400" />
          <span>{briefing.date}</span>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 text-xs text-slate-300 leading-relaxed font-sans">
        <div className="flex items-center gap-1.5 text-indigo-300 font-mono font-bold text-xs mb-1.5">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Institutional Macro Synthesis</span>
        </div>
        {briefing.executive_summary}
      </div>

      {/* 4 Pillars Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {briefing.key_drivers.map((driver, idx) => (
          <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">{driver.pillar}</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                {driver.stance}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed font-sans">{driver.takeaway}</p>
          </div>
        ))}
      </div>

      {/* Upcoming Catalysts */}
      <div className="pt-2 border-t border-white/5">
        <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 mb-2.5">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span>Key Macroeconomic Catalysts & Event Horizon</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {briefing.upcoming_catalysts.map((cat, idx) => (
            <div key={idx} className="p-2.5 rounded-lg bg-slate-900/40 border border-white/5 flex items-center justify-between text-xs font-mono">
              <div>
                <div className="text-slate-200 font-medium text-[11px]">{cat.event}</div>
                <div className="text-[10px] text-slate-500">{cat.frequency}</div>
              </div>
              <span className="text-[10px] text-cyan-400 font-bold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                {cat.expected_date}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
