import React from 'react';

interface StatsBarProps {
  onOpenAgents?: () => void;
  onOpenSources?: () => void;
}

export const StatsBar: React.FC<StatsBarProps> = ({ onOpenAgents, onOpenSources }) => {
  return (
    <div className="w-full flex justify-center items-center px-3 sm:px-8 z-20 mt-auto pb-4 sm:pb-8">
      <div className="w-full max-w-5xl glass-panel rounded-2xl px-4 sm:px-10 py-3.5 sm:py-5 shadow-2xl transition-all duration-300 hover:border-white/20">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 md:gap-8 items-center text-left">
          {/* Stat 1: Sector Agents */}
          <div 
            onClick={onOpenAgents}
            className="cursor-pointer group transition-transform duration-200 hover:-translate-y-0.5"
          >
            <div className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white tracking-tight group-hover:text-cyan-400 transition-colors">
              10+
            </div>
            <div className="text-[11px] sm:text-xs md:text-sm font-normal text-slate-300 mt-0.5">
              Sector Agents
            </div>
          </div>

          {/* Stat 2: Data Sources */}
          <div 
            onClick={onOpenSources}
            className="cursor-pointer group transition-transform duration-200 hover:-translate-y-0.5"
          >
            <div className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white tracking-tight group-hover:text-cyan-400 transition-colors">
              100+
            </div>
            <div className="text-[11px] sm:text-xs md:text-sm font-normal text-slate-300 mt-0.5">
              Data Sources
            </div>
          </div>

          {/* Stat 3: Real-time Insights */}
          <div className="group">
            <div className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white tracking-tight group-hover:text-cyan-400 transition-colors">
              Real-time
            </div>
            <div className="text-[11px] sm:text-xs md:text-sm font-normal text-slate-300 mt-0.5">
              Insights
            </div>
          </div>

          {/* Stat 4: Built for Bharat */}
          <div className="group">
            <div className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white tracking-tight group-hover:text-amber-400 transition-colors">
              Built for
            </div>
            <div className="text-[11px] sm:text-xs md:text-sm font-normal text-slate-300 mt-0.5">
              Bharat
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

