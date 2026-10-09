import React from 'react';
import { PieChart, Home, Factory, Building, Wheat } from 'lucide-react';
import { CreditSectoralBreakdown } from '../../types';

interface SectorBreakdownProps {
  sectoral?: CreditSectoralBreakdown | null;
  totalCredit?: number | null;
  onInspectEvidence?: () => void;
}

export const SectorBreakdown: React.FC<SectorBreakdownProps> = ({
  sectoral,
  totalCredit,
  onInspectEvidence,
}) => {

  const formatLakhCr = (val?: number | null) => {
    if (val == null) return '—';
    return `₹${(val / 100000).toFixed(2)} L Cr`;
  };

  const total = totalCredit || 1;

  const sectors = [
    {
      name: 'Personal Loans & Retail',
      val: sectoral?.personal_loans_cr ?? 0,
      color: 'from-cyan-500 to-blue-600',
      bgColor: 'bg-cyan-500',
      icon: Home,
      subtext: `Housing: ${formatLakhCr(sectoral?.personal_housing_cr)} • Vehicle: ${formatLakhCr(sectoral?.personal_vehicle_cr)}`,
    },
    {
      name: 'Services Sector',
      val: sectoral?.services_cr ?? 0,
      color: 'from-emerald-500 to-teal-600',
      bgColor: 'bg-emerald-500',
      icon: Building,
      subtext: 'Trade, NBFCs, Transport & Commercial Real Estate',
    },
    {
      name: 'Industry (MSME & Large)',
      val: (sectoral?.industry_msme_cr ?? 0) + (sectoral?.industry_large_cr ?? 0),
      color: 'from-indigo-500 to-violet-600',
      bgColor: 'bg-indigo-500',
      icon: Factory,
      subtext: `MSME: ${formatLakhCr(sectoral?.industry_msme_cr)} • Large: ${formatLakhCr(sectoral?.industry_large_cr)}`,
    },
    {
      name: 'Agriculture & Allied',
      val: sectoral?.agriculture_cr ?? 0,
      color: 'from-amber-500 to-orange-600',
      bgColor: 'bg-amber-500',
      icon: Wheat,
      subtext: 'Direct & Indirect farm credit support',
    },
  ];

  return (
    <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-5 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-2">
              <PieChart className="w-4 h-4 text-emerald-400" />
              <span>Sectoral Deployment of Non-Food Credit</span>
            </h3>
            <button
              onClick={onInspectEvidence}
              className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
            >
              RBI r539
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical allocation of ₹{(total / 100000).toFixed(2)} L Cr across productive economic sectors
          </p>
        </div>

        {/* Stacked Proportional Bar Preview */}
        <div className="w-full sm:w-48 h-3 rounded-full bg-slate-800/80 overflow-hidden flex p-0.5 gap-0.5 border border-white/5">
          {sectors.map((s, i) => {
            const pct = total > 0 ? (s.val / total) * 100 : 0;
            return (
              <div
                key={i}
                className={`h-full rounded-full ${s.bgColor}`}
                style={{ width: `${pct}%` }}
                title={`${s.name}: ${pct.toFixed(1)}%`}
              />
            );
          })}
        </div>
      </div>

      {/* Sector Rows */}
      <div className="space-y-3.5 pt-1">
        {sectors.map((sec, idx) => {
          const share = total > 0 && sec.val > 0 ? ((sec.val / total) * 100).toFixed(1) : '0';
          const Icon = sec.icon;

          return (
            <div
              key={idx}
              className="p-3 rounded-xl bg-slate-900/50 border border-white/5 hover:border-white/15 transition-all group"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-lg bg-white/5 text-slate-300 group-hover:text-white transition-colors`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="font-medium text-slate-200">{sec.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-white font-mono font-bold text-sm">
                    {formatLakhCr(sec.val)}
                  </span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-slate-300 border border-white/10 font-semibold">
                    {share}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${sec.color} transition-all duration-700`}
                  style={{ width: `${Math.min(100, Math.max(0, Number(share)))}%` }}
                />
              </div>

              <div className="text-[10px] text-slate-400 font-mono mt-1.5 flex items-center justify-between">
                <span>{sec.subtext}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
