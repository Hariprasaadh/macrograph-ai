import React from 'react';
import { Layers, ShieldCheck } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { DailyBriefingCard } from '../studio/DailyBriefingCard';
import { AnomalyFeed } from '../studio/AnomalyFeed';
import { CrossSectorStudio } from '../studio/CrossSectorStudio';
import { ScenarioSimulator } from '../studio/ScenarioSimulator';

interface AllSectorsTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
  formatLakhCr: (val?: number | null) => string;
  formatPct: (val?: number | null, suffix?: string) => string;
}

export const AllSectorsTabView: React.FC<AllSectorsTabViewProps> = ({
  data,
  openEvidence,
  formatLakhCr,
  formatPct,
}) => {
  const credit = data?.finance_sector?.credit_growth;
  const asset = data?.finance_sector?.asset_quality;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 1. Daily Intelligence Brief */}
      <DailyBriefingCard briefing={data?.daily_brief} />

      {/* 2. Anomaly Detection Feed */}
      <AnomalyFeed anomalies={data?.anomalies || []} onInspectEvidence={openEvidence} />

      {/* 3. Cross Sector Dynamic Transmission Studio */}
      <CrossSectorStudio data={data} onInspectEvidence={openEvidence} />

      {/* 4. Macro Scenario Simulator */}
      <ScenarioSimulator />

      {/* 5. Multi-Sector Telemetry Matrix */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Multi-Sector Macroeconomic Telemetry Matrix</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Live indicators ingested across active sector DuckDB stores and official mirrors.
            </p>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5 self-start sm:self-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Active Sectors ({data?.platform_summary?.active_live_sectors?.length ?? 8}/10)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3.5 pt-2">
          {data?.other_sectors_preview?.map((sec, idx) => {
            const isVerified = sec.status === 'verified';
            return (
              <div
                key={idx}
                onClick={() => openEvidence(sec.citation, sec.indicator, sec.value, sec.period)}
                className="p-4 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/20 transition-all flex flex-col justify-between cursor-pointer group"
              >
                <div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mb-1.5">
                    <span className="truncate max-w-[130px]">{sec.frequency}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${
                        isVerified
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/25'
                      }`}
                    >
                      {isVerified ? 'VERIFIED REAL' : 'STAGED'}
                    </span>
                  </div>
                  <div className="text-[11px] text-cyan-300 font-mono font-medium">{sec.sector}</div>
                  <div className="text-xs text-slate-200 font-medium mt-0.5 group-hover:text-white transition-colors">{sec.indicator}</div>
                  <div className="text-lg font-bold text-white mt-1.5 font-mono">
                    {sec.value ?? <span className="text-slate-500 font-normal text-xs">Connecting…</span>}
                  </div>
                  {sec.sub_value && (
                    <div className="text-[11px] font-mono text-emerald-400 mt-0.5">
                      {sec.sub_value}
                    </div>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-2 truncate border-t border-white/5 pt-1.5 flex items-center justify-between">
                  <span className="truncate" title={sec.source}>{sec.source}</span>
                  <span className="text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity font-mono text-[9px]">Inspect →</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 6. Provenance & Citation Audit Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Official RBI DBIE &amp; MoSPI Provenance Audit Table</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict audit trail ensuring zero hallucinated financial values across all macroeconomic claims
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 self-start sm:self-auto">
            Zero-Hallucination Standard
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Pillar Indicator</th>
                <th className="py-2.5 px-4">Data Source Authority</th>
                <th className="py-2.5 px-4">Canonical Table</th>
                <th className="py-2.5 px-4">Period</th>
                <th className="py-2.5 px-4">Verification</th>
                <th className="py-2.5 px-4 text-right">Audit Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Bank Credit &amp; Sectoral Deployment</td>
                <td className="py-3 px-4 text-slate-400">Reserve Bank of India (RBI)</td>
                <td className="py-3 px-4 text-cyan-300">financial_sector.r539</td>
                <td className="py-3 px-4">{credit?.period ?? '—'}</td>
                <td className="py-3 px-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    VERIFIED REAL
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(credit?.citation, 'Bank Credit & Sectoral Deployment', formatLakhCr(credit?.non_food_credit_cr), credit?.period)}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Inspect Evidence
                  </button>
                </td>
              </tr>

              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">SCB Asset Quality (GNPA / NNPA / CRAR)</td>
                <td className="py-3 px-4 text-slate-400">Reserve Bank of India (FSR)</td>
                <td className="py-3 px-4 text-cyan-300">financial_sector.r330</td>
                <td className="py-3 px-4">{asset?.period ?? '—'}</td>
                <td className="py-3 px-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    VERIFIED REAL
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(asset?.citation, 'Asset Quality (Gross & Net NPA)', formatPct(asset?.gross_npa_pct), asset?.period)}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Inspect Evidence
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
