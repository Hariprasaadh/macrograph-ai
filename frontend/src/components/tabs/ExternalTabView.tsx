import React, { useMemo } from 'react';
import { Globe, ArrowUpRight } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { SectorDbieTableWidget } from '../charts/SectorDbieTableWidget';
import { TiltCard } from '../motion/TiltCard';

interface ExternalTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

export const ExternalTabView: React.FC<ExternalTabViewProps> = ({ data, openEvidence }) => {
  const ext = data?.external_sector;
  const latestFx = ext?.latest_fx;
  const latestRes = ext?.latest_reserves;
  const latestTrade = ext?.latest_trade;
  const tradeHistory = ext?.trade_history || [];

  const fxChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.fx) return [];
    return data.timeseries.fx.map((pt) => ({
      period: pt.period,
      value: pt.usd_inr_rate,
      label: 'USD / INR',
    }));
  }, [data]);

  const reservesChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.reserves) return [];
    return data.timeseries.reserves.map((pt) => ({
      period: pt.period,
      value: Number((pt.total_reserves_usd_mn / 1000).toFixed(1)),
      label: 'Forex Reserves ($ Bn)',
    }));
  }, [data]);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* External Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="USD/INR Exchange Rate" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>USD / INR Reference Rate</span>
                <button
                  onClick={() => openEvidence(latestFx?.citation, 'USD / INR Reference Rate', `₹${latestFx?.usd_inr_rate?.toFixed(2)}`, latestFx?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  RBI FBIL
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                ₹{latestFx?.usd_inr_rate?.toFixed(2) || '85.57'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Orderly RBI Market Interventions</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Period: <strong className="text-slate-200 font-mono">{latestFx?.period || 'Latest Daily'}</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Foreign Exchange Reserves" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Total Forex Reserves</span>
                <button
                  onClick={() => openEvidence(latestRes?.citation, 'Total Forex Reserves', `$${((latestRes?.total_reserves_usd_mn || 700000) / 1000).toFixed(1)} Bn`, latestRes?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  RBI WSS
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                ${((latestRes?.total_reserves_usd_mn || 700200) / 1000).toFixed(1)} Bn
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 flex items-center gap-0.5 border border-emerald-500/25 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  Historic Peak
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Import Cover: <strong className="text-slate-200 font-mono">&gt; 11.4 Months</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Monthly Merchandise Exports" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Merchandise Exports</span>
                <button
                  onClick={() => openEvidence(latestTrade?.citation, 'Merchandise Exports', `$${latestTrade?.exports_usd_bn} Bn`, latestTrade?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  MoC&amp;I
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                ${latestTrade?.exports_usd_bn || '38.1'} Bn
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Imports: ${latestTrade?.imports_usd_bn || '60.1'} Bn</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-amber-400 truncate border-t border-white/5 pt-2 font-mono">
              Trade Deficit: -${latestTrade?.trade_deficit_usd_bn || '22.0'} Bn
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Current Account Deficit" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Current Account Deficit</span>
                <button
                  onClick={() => openEvidence(null, 'Current Account Deficit to GDP', '-0.8% of GDP', 'FY25')}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  CAD / GDP
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-2 font-mono tracking-tight">
                -0.8% of GDP
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 font-mono border border-emerald-500/25">
                  Comfort Zone (&lt; 2.5%)
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Remittances: <strong className="text-slate-200 font-mono">$125 Bn / year (Global #1)</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
        <TimeSeriesChart
          title="USD / INR FBIL Reference Rate Dynamics"
          subtitle="Daily central bank reference rate for sovereign currency valuation"
          data={fxChartData}
          valuePrefix="₹"
          color="indigo"
          onInspectEvidence={() =>
            openEvidence(latestFx?.citation, 'USD / INR Reference Rate Time Series', `₹${latestFx?.usd_inr_rate}`, latestFx?.period)
          }
        />

        <TimeSeriesChart
          title="Foreign Exchange Reserves Accumulation"
          subtitle="Chronological trajectory of foreign currency assets, gold, and SDR reserves"
          data={reservesChartData}
          valuePrefix="$"
          valueSuffix=" Bn"
          color="emerald"
          onInspectEvidence={() =>
            openEvidence(latestRes?.citation, 'Foreign Exchange Reserves Time Series', `$${latestRes?.total_reserves_usd_mn} Mn`, latestRes?.period)
          }
        />
      </div>

      {/* Merchandise Trade Historical Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Globe className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                Merchandise Trade Balance &amp; External Exposure Breakdown
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Monthly trade flows published by Department of Commerce &amp; RBI DBIE
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            DuckDB Ingested
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Period</th>
                <th className="py-2.5 px-4 text-right">Exports ($ Bn)</th>
                <th className="py-2.5 px-4 text-right">Imports ($ Bn)</th>
                <th className="py-2.5 px-4 text-right">Trade Deficit ($ Bn)</th>
                <th className="py-2.5 px-4 text-right">Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {tradeHistory.map((tr, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 text-white font-medium">{tr.period}</td>
                  <td className="py-3 px-4 text-right text-emerald-400 font-bold">${tr.exports_usd_bn.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right text-slate-300 font-bold">${tr.imports_usd_bn.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right text-amber-400 font-bold">-${tr.trade_deficit_usd_bn.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => openEvidence(tr.citation, `Trade Balance (${tr.period})`, `Deficit -$${tr.trade_deficit_usd_bn} Bn`, tr.period)}
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

      {/* RBI DBIE Official External Sector & Forex Telemetry Tables & Charts */}
      {data?.rbi_dbie_live?.sector_tables?.['external'] && (
        <SectorDbieTableWidget
          sectorKey="external"
          sectorName="External Sector & Forex"
          tables={data.rbi_dbie_live.sector_tables['external']}
          openEvidence={openEvidence}
          accentColor="cyan"
        />
      )}
    </div>
  );
};
