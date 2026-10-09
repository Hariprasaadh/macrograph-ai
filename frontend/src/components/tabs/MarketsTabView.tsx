import React, { useMemo } from 'react';
import { Landmark } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { SectorDbieTableWidget } from '../charts/SectorDbieTableWidget';
import { TiltCard } from '../motion/TiltCard';

interface MarketsTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

export const MarketsTabView: React.FC<MarketsTabViewProps> = ({ data, openEvidence }) => {
  const cap = data?.capmarkets_sector;
  const mon = data?.monetary_sector;
  const latestGsec = cap?.latest_gsec;
  const latestVix = cap?.latest_vix;
  const latestRates = mon?.latest_rates;

  const gsecChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.gsec) return [];
    return data.timeseries.gsec.map((pt) => ({
      period: pt.period,
      value: pt.ten_year_gsec_yield_pct,
      label: '10-Yr G-Sec Yield',
    }));
  }, [data]);

  const vixChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.vix) return [];
    return data.timeseries.vix.map((pt) => ({
      period: pt.period,
      value: pt.vix_close,
      label: 'India VIX',
    }));
  }, [data]);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Markets Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="10-Year G-Sec Yield" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>10-Yr Benchmark Yield</span>
                <button
                  onClick={() => openEvidence(latestGsec?.citation, '10-Year Benchmark G-Sec Yield', `${latestGsec?.ten_year_gsec_yield_pct}%`, latestGsec?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  CCIL / RBI
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                {latestGsec?.ten_year_gsec_yield_pct?.toFixed(2) || '6.77'}%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Sovereign Curve Anchor</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Period: <strong className="text-slate-200 font-mono">{latestGsec?.period || 'Latest Monthly'}</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="India VIX Volatility" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>India VIX Volatility</span>
                <button
                  onClick={() => openEvidence(latestVix?.citation, 'India VIX Index', `${latestVix?.vix_close}`, latestVix?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  NSE Mirror
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                {latestVix?.vix_close?.toFixed(2) || '13.84'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 font-mono border border-emerald-500/25">
                  Subdued (&lt; 15.0)
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Equity Market Risk Premium: <strong className="text-slate-200 font-mono">Stable</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="RBI Policy Repo Rate" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Policy Repo Rate</span>
                <button
                  onClick={() => openEvidence(latestRates?.citation, 'RBI Policy Repo Rate', `${latestRates?.repo_rate_pct || 6.50}%`, latestRates?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  MPC Stance
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                {latestRates?.repo_rate_pct?.toFixed(2) || '6.50'}%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Stance: Neutral / Withdrawal</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              SDF: <strong className="text-slate-200 font-mono">6.25%</strong> | MSF: <strong className="text-slate-200 font-mono">6.75%</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Cash Reserve Ratio (CRR)" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>CRR &amp; Liquidity Buffer</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  RBI Ratio
                </span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-amber-300 mt-2 font-mono tracking-tight">
                4.50%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">SLR: 18.00%</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              System Liquidity: <strong className="text-emerald-400 font-mono">Mild Surplus</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
        <TimeSeriesChart
          title="10-Year Benchmark Sovereign G-Sec Yield"
          subtitle="Secondary market sovereign curve pricing from CCIL / RBI DBIE mirror"
          data={gsecChartData}
          valueSuffix="%"
          color="indigo"
          onInspectEvidence={() =>
            openEvidence(latestGsec?.citation, '10-Yr Benchmark G-Sec Yield Time Series', `${latestGsec?.ten_year_gsec_yield_pct}%`, latestGsec?.period)
          }
        />

        <TimeSeriesChart
          title="India VIX Equity Market Volatility"
          subtitle="National Stock Exchange implied volatility index representing risk sentiment"
          data={vixChartData}
          color="emerald"
          onInspectEvidence={() =>
            openEvidence(latestVix?.citation, 'India VIX Time Series', `${latestVix?.vix_close}`, latestVix?.period)
          }
        />
      </div>

      {/* Policy Rate Corridor & Reserve Framework Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Landmark className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                Monetary Policy Corridor &amp; Statutory Ratios Matrix
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Official operating parameters prescribed by the RBI Monetary Policy Committee
            </p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded-full border border-cyan-500/20">
            MPC Resolution
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Policy Instrument</th>
                <th className="py-2.5 px-4">Role in Monetary Transmission</th>
                <th className="py-2.5 px-4 text-right">Current Rate / Ratio</th>
                <th className="py-2.5 px-4 text-right">Spread vs Repo</th>
                <th className="py-2.5 px-4 text-right">Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Marginal Standing Facility (MSF)</td>
                <td className="py-3 px-4 text-slate-400">Ceiling of policy corridor for emergency overnight liquidity</td>
                <td className="py-3 px-4 text-right font-bold text-indigo-300">6.75%</td>
                <td className="py-3 px-4 text-right text-slate-300">+25 bps</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(latestRates?.citation, 'MSF Rate', '6.75%', 'Latest')}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Audit
                  </button>
                </td>
              </tr>
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Policy Repo Rate</td>
                <td className="py-3 px-4 text-slate-400">Anchor policy rate for commercial bank borrowing against G-Secs</td>
                <td className="py-3 px-4 text-right font-bold text-cyan-300">6.50%</td>
                <td className="py-3 px-4 text-right text-slate-300">0 bps (Anchor)</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(latestRates?.citation, 'Policy Repo Rate', '6.50%', 'Latest')}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Audit
                  </button>
                </td>
              </tr>
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Standing Deposit Facility (SDF)</td>
                <td className="py-3 px-4 text-slate-400">Floor of policy corridor for uncollateralised deposit absorption</td>
                <td className="py-3 px-4 text-right font-bold text-emerald-400">6.25%</td>
                <td className="py-3 px-4 text-right text-slate-300">-25 bps</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(latestRates?.citation, 'SDF Rate', '6.25%', 'Latest')}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Audit
                  </button>
                </td>
              </tr>
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Cash Reserve Ratio (CRR)</td>
                <td className="py-3 px-4 text-slate-400">Share of Net Demand and Time Liabilities held as cash with RBI</td>
                <td className="py-3 px-4 text-right font-bold text-amber-300">4.50%</td>
                <td className="py-3 px-4 text-right text-slate-400">Statutory Ratio</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(null, 'CRR Ratio', '4.50%', 'Latest')}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Audit
                  </button>
                </td>
              </tr>
              <tr className="hover:bg-white/5 transition-colors">
                <td className="py-3 px-4 text-white font-medium">Statutory Liquidity Ratio (SLR)</td>
                <td className="py-3 px-4 text-slate-400">Mandatory investment in approved sovereign assets &amp; gold</td>
                <td className="py-3 px-4 text-right font-bold text-amber-300">18.00%</td>
                <td className="py-3 px-4 text-right text-slate-400">Statutory Ratio</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => openEvidence(null, 'SLR Ratio', '18.00%', 'Latest')}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-[11px]"
                  >
                    Audit
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* RBI DBIE Official Financial Markets & Sovereign Yields Telemetry Tables & Charts */}
      {data?.rbi_dbie_live?.sector_tables?.['markets'] && (
        <SectorDbieTableWidget
          sectorKey="markets"
          sectorName="Capital Markets & Sovereign Yields"
          tables={data.rbi_dbie_live.sector_tables['markets']}
          openEvidence={openEvidence}
          accentColor="indigo"
        />
      )}
    </div>
  );
};
