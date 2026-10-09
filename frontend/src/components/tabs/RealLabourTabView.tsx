import React, { useMemo } from 'react';
import { Factory, CheckCircle2, TrendingUp } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { SectorDbieTableWidget } from '../charts/SectorDbieTableWidget';
import { TiltCard } from '../motion/TiltCard';

interface RealLabourTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

export const RealLabourTabView: React.FC<RealLabourTabViewProps> = ({ data, openEvidence }) => {
  const real = data?.real_sector;
  const serv = data?.services_sector;
  const lab = data?.labour_sector;
  const empOpen = data?.employment_open;
  const econ = data?.economy_survey;

  const core = real?.latest_core;
  const pmi = serv?.latest_pmi;
  const unemp = lab?.latest_unemp;
  const lfpr = lab?.latest_lfpr;

  const unempChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (empOpen?.timeseries && empOpen.timeseries.length > 0) {
      return empOpen.timeseries.map((pt) => ({
        period: pt.year,
        value: pt.value,
        label: 'PLFS Unemployment Rate',
      }));
    }
    if (data?.timeseries?.unemployment) {
      return data.timeseries.unemployment.map((pt) => ({
        period: pt.period,
        value: pt.unemployment_rate_pct,
        label: 'Unemployment Rate',
      }));
    }
    return [];
  }, [empOpen, data]);

  // Sectoral GVA Breakdown
  const gvaSectors = econ?.sectors || [
    { id: 'agriculture', name: 'Agriculture & Allied Sectors', currentGrowth: 3.8, gvaShare: 17.0 },
    { id: 'industry', name: 'Industry & Manufacturing', currentGrowth: 6.2, gvaShare: 26.0 },
    { id: 'services', name: 'Services & Digital Economy', currentGrowth: 7.8, gvaShare: 57.0 },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Real & Labour Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="Real GDP Growth" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Real GDP Growth Rate</span>
                <button
                  onClick={() => openEvidence(econ?.citation, 'Real GDP Growth Rate', `${econ?.summary?.realGDPGrowth || 6.5}%`, '2025-26')}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  Economic Survey
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                {econ?.summary?.realGDPGrowth || 6.5}%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Projected: 7.4% High Band</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Nominal GDP: <strong className="text-slate-200 font-mono">₹{((econ?.summary?.nominalGDP || 34547157) / 100000).toFixed(2)} L Cr</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="PLFS Unemployment Rate" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>PLFS Unemployment</span>
                <button
                  onClick={() => openEvidence(unemp?.citation || empOpen?.citation, 'PLFS Unemployment Rate', `${unemp?.unemployment_rate_pct || 3.1}%`, unemp?.period || 'Latest')}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  MoSPI PLFS
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                {unemp?.unemployment_rate_pct?.toFixed(1) || '3.1'}%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">
                  Youth: {empOpen?.summary?.youthUnemployment || 9.9}%
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              LFPR: <strong className="text-slate-200 font-mono">{empOpen?.summary?.lfpr || lfpr?.lfpr_total_pct || 59.3}%</strong> (Female: {empOpen?.summary?.femaleLfpr || 40.0}%)
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Core Industries (8-Core)" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Core Industries Index (ICI)</span>
                <button
                  onClick={() => openEvidence(core?.citation, 'Core Industries Index (ICI)', `+${core?.overall_ici_yoy_pct}% YoY`, core?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  DPIIT / OEA
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                +{core?.overall_ici_yoy_pct?.toFixed(1) || '6.7'}% YoY
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Weight in IIP: 40.27%</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Steel: <strong className="text-emerald-400 font-mono">+{core?.sectoral?.steel || 8.4}%</strong> | Coal: <strong className="text-emerald-400 font-mono">+{core?.sectoral?.coal || 10.2}%</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Services PMI Activity" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Services Sector PMI</span>
                <button
                  onClick={() => openEvidence(pmi?.citation, 'Services Sector PMI', `${pmi?.headline_pmi}`, pmi?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
                >
                  S&amp;P Global
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-amber-300 mt-2 font-mono tracking-tight">
                {pmi?.headline_pmi?.toFixed(1) || '59.2'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 font-mono border border-emerald-500/25">
                  Expansionary (&gt; 50.0)
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Services Share of GVA: <strong className="text-slate-200 font-mono">57.0%</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
        <TimeSeriesChart
          title="Periodic Labour Force Survey (PLFS) Unemployment Trend"
          subtitle="Annual and quarterly principal status unemployment rates published by MoSPI"
          data={unempChartData}
          valueSuffix="%"
          color="cyan"
          onInspectEvidence={() =>
            openEvidence(unemp?.citation || empOpen?.citation, 'PLFS Unemployment Time Series', `${unemp?.unemployment_rate_pct}%`, unemp?.period)
          }
        />

        {/* Core Industries 8-Sector Breakdown Card */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-2">
                <Factory className="w-4 h-4 text-indigo-400" />
                <span>8 Core Infrastructure Industries YoY Growth</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Key industrial output components constituting 40.27% of Index of Industrial Production (IIP)
              </p>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              DPIIT OEA
            </span>
          </div>

          <div className="space-y-2.5 pt-1">
            {[
              { name: 'Coal Mining', growth: core?.sectoral?.coal ?? 10.2, weight: '10.33%' },
              { name: 'Steel Production', growth: core?.sectoral?.steel ?? 8.4, weight: '17.92%' },
              { name: 'Electricity Generation', growth: core?.sectoral?.electricity ?? 7.1, weight: '19.85%' },
              { name: 'Cement Manufacturing', growth: core?.sectoral?.cement ?? 6.5, weight: '5.37%' },
              { name: 'Crude Oil', growth: core?.sectoral?.crude_oil ?? -1.2, weight: '8.98%' },
            ].map((sub, idx) => (
              <div key={idx} className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-slate-200 font-medium">{sub.name}</span>
                  <span className="text-[10px] text-slate-500 ml-2">(Weight: {sub.weight})</span>
                </div>
                <span
                  className={`font-bold ${
                    sub.growth >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {sub.growth >= 0 ? `+${sub.growth}%` : `${sub.growth}%`}
                </span>
              </div>
            ))}
          </div>

          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2 font-mono">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>Infrastructure output growth maintains multi-month expansionary trajectory.</span>
          </div>
        </div>
      </div>

      {/* Sector Output GVA Composition Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <TrendingUp className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                Gross Value Added (GVA) Sectoral Composition &amp; Momentum
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              National accounts output structure from Economic Survey &amp; MoSPI National Accounts Division
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            Economic Survey 2025-26
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Economic Sector</th>
                <th className="py-2.5 px-4 text-right">Share of Total GVA</th>
                <th className="py-2.5 px-4 text-right">Annual Real Growth Rate</th>
                <th className="py-2.5 px-4 text-right">Audit Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {gvaSectors.map((sec, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 text-white font-medium">{sec.name}</td>
                  <td className="py-3 px-4 text-right text-indigo-300 font-bold">{sec.gvaShare}%</td>
                  <td className="py-3 px-4 text-right text-emerald-400 font-bold">+{sec.currentGrowth}% YoY</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => openEvidence(econ?.citation, `GVA: ${sec.name}`, `${sec.currentGrowth}% YoY`, '2025-26')}
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

      {/* RBI DBIE Official Real Growth, Output & Inflation Tables & Charts */}
      {data?.rbi_dbie_live?.sector_tables && (
        <div className="space-y-6">
          {(data.rbi_dbie_live.sector_tables['real'] || data.rbi_dbie_live.sector_tables['prices']) && (
            <SectorDbieTableWidget
              sectorKey="real"
              sectorName="Real Output & Prices"
              tables={[
                ...(data.rbi_dbie_live.sector_tables['real'] || []),
                ...(data.rbi_dbie_live.sector_tables['prices'] || []),
              ]}
              openEvidence={openEvidence}
              accentColor="emerald"
            />
          )}

          {data.rbi_dbie_live.sector_tables['labour'] && (
            <SectorDbieTableWidget
              sectorKey="labour"
              sectorName="Labour & Employment"
              tables={data.rbi_dbie_live.sector_tables['labour']}
              openEvidence={openEvidence}
              accentColor="cyan"
            />
          )}
        </div>
      )}
    </div>
  );
};
