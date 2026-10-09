import React from 'react';
import { MapPin } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TiltCard } from '../motion/TiltCard';

interface StatesTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

export const StatesTabView: React.FC<StatesTabViewProps> = ({ data, openEvidence }) => {
  const stateFin = data?.state_finances;
  const summary = stateFin?.summary;
  const states = stateFin?.states || [];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* States Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="National GSDP Total" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>National GSDP Aggregate</span>
                <button
                  onClick={() => openEvidence(stateFin?.citation, 'National GSDP Total', `₹${summary?.nationalGsdpTotal} L Cr`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  RBI States
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                ₹{summary?.nationalGsdpTotal || '272.2'} L Cr
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">
                  States Reporting: {summary?.statesWithData || 31} / {summary?.totalStatesAndUTs || 36}
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Growth Range: <strong className="text-emerald-400 font-mono">{summary?.growthRange || '2.8% – 18.1%'}</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Top GSDP State" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Top GSDP Economy</span>
                <button
                  onClick={() => openEvidence(stateFin?.citation, 'Top State GSDP (Maharashtra)', `₹${summary?.topGsdpValue} L Cr`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
                >
                  #1 State
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-amber-300 mt-2 font-mono tracking-tight">
                {summary?.topGsdpState || 'Maharashtra'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 font-mono border border-amber-500/25">
                  ₹{summary?.topGsdpValue || '36.42'} L Cr
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Share of India GSDP: <strong className="text-slate-200 font-mono">~13.4%</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Average Per-Capita Income" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>National Avg Per-Capita</span>
                <button
                  onClick={() => openEvidence(stateFin?.citation, 'Average Per-Capita NSDP', `₹${summary?.averagePerCapita?.toLocaleString()}`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  NSDP Per Capita
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                ₹{summary?.averagePerCapita ? summary.averagePerCapita.toLocaleString() : '1,74,343'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Annual Net State Domestic Product</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              High Range: <strong className="text-emerald-400 font-mono">₹3.10L (Karnataka)</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Inter-State Convergence" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Fiscal Capacity Index</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Devolution
                </span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                41.0%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">15th Finance Commission Tax Share</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              State Own Tax Revenue: <strong className="text-slate-200 font-mono">Growing at +14% YoY</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* State GSDP Leaderboard Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <MapPin className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                State GSDP &amp; Economic Momentum Leaderboard
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Official sub-national output, growth rates, and per-capita incomes from the RBI Handbook of Statistics on Indian States
            </p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded-full border border-cyan-500/20 self-start sm:self-auto">
            RBI Handbook Mirror
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Rank &amp; State</th>
                <th className="py-2.5 px-4 text-right">Nominal GSDP (₹ Cr)</th>
                <th className="py-2.5 px-4 text-right">GSDP (₹ Lakh Cr)</th>
                <th className="py-2.5 px-4 text-right">Growth Rate (% YoY)</th>
                <th className="py-2.5 px-4 text-right">Per Capita NSDP (₹)</th>
                <th className="py-2.5 px-4 text-right">Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {states.map((st, idx) => (
                <tr key={st.id || idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 text-white font-medium flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-400 text-[10px] flex items-center justify-center font-mono">
                      {idx + 1}
                    </span>
                    <span>{st.name}</span>
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-amber-300">
                    ₹{st.gsdp.toLocaleString()} Cr
                  </td>
                  <td className="py-3 px-4 text-right text-slate-300">
                    ₹{(st.gsdp / 100000).toFixed(2)} L Cr
                  </td>
                  <td className="py-3 px-4 text-right text-emerald-400 font-bold">
                    +{st.growthRate}%
                  </td>
                  <td className="py-3 px-4 text-right text-cyan-300">
                    ₹{st.perCapitaNsdp ? st.perCapitaNsdp.toLocaleString() : '—'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => openEvidence(stateFin?.citation, `GSDP: ${st.name}`, `₹${(st.gsdp / 100000).toFixed(2)} L Cr`, 'Latest')}
                      className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                    >
                      Audit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
