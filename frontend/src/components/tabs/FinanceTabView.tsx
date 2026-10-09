import React, { useState } from 'react';
import { ShieldCheck, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { RadialGauge } from '../charts/RadialGauge';
import { SectorBreakdown } from '../charts/SectorBreakdown';
import { SectorDbieTableWidget } from '../charts/SectorDbieTableWidget';
import { TiltCard } from '../motion/TiltCard';

interface FinanceTabViewProps {
  data: DashboardOverview | null;
  creditChartData: TimeSeriesDataPoint[];
  ratesChartData: TimeSeriesDataPoint[];
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
  formatLakhCr: (val?: number | null) => string;
  formatPct: (val?: number | null, suffix?: string) => string;
}

export const FinanceTabView: React.FC<FinanceTabViewProps> = ({
  data,
  creditChartData,
  ratesChartData,
  openEvidence,
  formatLakhCr,
  formatPct,
}) => {
  const [activeChart, setActiveChart] = useState<'credit' | 'rates'>('credit');
  const finance = data?.finance_sector;
  const credit = finance?.credit_growth;
  const asset = finance?.asset_quality;
  const rates = finance?.lending_rates;
  const deposits = finance?.deposits_cd_ratio;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Finance Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="Bank credit expansion" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Non-Food Bank Credit</span>
                <button
                  onClick={() => openEvidence(credit?.citation, 'Non-Food Bank Credit Deployment', formatLakhCr(credit?.non_food_credit_cr), credit?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  RBI r539
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-2 font-mono tracking-tight">
                {formatLakhCr(credit?.non_food_credit_cr)}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 flex items-center gap-0.5 border border-emerald-500/25 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  {formatPct(credit?.non_food_credit_yoy_pct)} YoY
                </span>
                <span className="text-[11px] text-slate-500 font-mono">{credit?.period}</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Gross Volume: <strong className="text-slate-200 font-mono">{formatLakhCr(credit?.gross_credit_cr)}</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Banking asset health" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Gross NPA (SCBs)</span>
                <button
                  onClick={() => openEvidence(asset?.citation, 'Scheduled Commercial Banks Gross NPA', formatPct(asset?.gross_npa_pct), asset?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  RBI r330
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                {formatPct(asset?.gross_npa_pct)}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-300 flex items-center gap-0.5 border border-cyan-500/25 font-mono">
                  <ArrowDownRight className="w-3.5 h-3.5" />
                  Net: {formatPct(asset?.net_npa_pct)}
                </span>
                <span className="text-[11px] text-slate-500 font-mono">PCR: {formatPct(asset?.provision_coverage_ratio_pct)}</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Solvency CRAR: <strong className="text-slate-200 font-mono">{formatPct(asset?.crar_pct)}</strong> (CET-1: {formatPct(asset?.cet1_pct)})
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Lending rate structure" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Fresh Lending Rate (WALR)</span>
                <button
                  onClick={() => openEvidence(rates?.citation, 'Fresh Rupee Lending Rate (WALR)', formatPct(rates?.walr_fresh_pct), rates?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  RBI r531
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                {formatPct(rates?.walr_fresh_pct)}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-300 font-mono border border-indigo-500/25">
                  1-Yr MCLR: {formatPct(rates?.mclr_1yr_median_pct)}
                </span>
                <span className="text-[11px] text-slate-500 font-mono">Deposit: {formatPct(rates?.wadtdr_fresh_pct)}</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Outstanding WALR: <strong className="text-slate-200 font-mono">{formatPct(rates?.walr_outstanding_pct)}</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Aggregate deposits" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Aggregate Deposits</span>
                <button
                  onClick={() => openEvidence(deposits?.citation, 'Commercial Bank Deposits & CD Ratio', formatLakhCr(deposits?.aggregate_deposits_cr), deposits?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
                >
                  RBI r689
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-2 font-mono tracking-tight">
                {formatLakhCr(deposits?.aggregate_deposits_cr)}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 flex items-center gap-0.5 border border-amber-500/25 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  {deposits?.deposits_yoy_pct != null ? `+${deposits.deposits_yoy_pct}% YoY` : '—'}
                </span>
                <span className="text-[11px] text-slate-500 font-mono">CD: {formatPct(deposits?.cd_ratio_pct)}</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              CASA Ratio: <strong className="text-slate-200 font-mono">{formatPct(deposits?.casa_ratio_pct)}</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Main Charts & Solvency Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Empirical Trajectory
            </span>
            <div className="flex items-center gap-1 bg-slate-900/60 p-0.5 rounded-xl border border-white/5">
              <button
                onClick={() => setActiveChart('credit')}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-all ${
                  activeChart === 'credit' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Credit Growth
              </button>
              <button
                onClick={() => setActiveChart('rates')}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-all ${
                  activeChart === 'rates' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Rates Spread
              </button>
            </div>
          </div>

          {activeChart === 'credit' ? (
            <TimeSeriesChart
              title="Non-Food Credit Deployment Volume"
              subtitle="Chronological historical progression ingested from RBI DBIE r539"
              data={creditChartData}
              valuePrefix="₹"
              valueSuffix=" L Cr"
              secondaryLabel="YoY Growth"
              secondarySuffix="%"
              color="emerald"
              onInspectEvidence={() =>
                openEvidence(credit?.citation, 'Non-Food Bank Credit Time Series', formatLakhCr(credit?.non_food_credit_cr), credit?.period)
              }
            />
          ) : (
            <TimeSeriesChart
              title="Fresh Lending Rate (WALR) Dynamics"
              subtitle="Policy rate pass-through and weighted average lending rates"
              data={ratesChartData}
              valueSuffix="%"
              secondaryLabel="Deposit WADTDR"
              secondarySuffix="%"
              color="indigo"
              onInspectEvidence={() =>
                openEvidence(rates?.citation, 'Lending Rates Time Series', formatPct(rates?.walr_fresh_pct), rates?.period)
              }
            />
          )}
        </div>

        {/* SCB Solvency Radial Gauges */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-5 shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                <span>Scheduled Commercial Banks Solvency Gauges</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Financial Stability Report (FSR) capital adequacy and provisioning buffers
              </p>
            </div>
            <button
              onClick={() => openEvidence(asset?.citation, 'SCB Asset Quality Metrics', formatPct(asset?.gross_npa_pct), asset?.period)}
              className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
            >
              RBI r330 / r329
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <RadialGauge
              title="Capital Adequacy (CRAR)"
              value={asset?.crar_pct ?? 16.8}
              target={11.5}
              targetLabel="Reg. Min"
              subtext="Healthy +530 bps safety buffer"
              color="emerald"
            />
            <RadialGauge
              title="Provision Coverage (PCR)"
              value={asset?.provision_coverage_ratio_pct ?? 76.4}
              target={70.0}
              targetLabel="Prudent Min"
              subtext="Robust buffer against loan losses"
              color="cyan"
            />
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between text-xs font-mono">
            <div className="text-slate-400">CET-1 Core Capital Share:</div>
            <div className="text-white font-bold">{formatPct(asset?.cet1_pct)}</div>
          </div>
        </div>
      </div>

      {/* Credit Sectoral Breakdown */}
      <SectorBreakdown
        sectoral={credit?.sectoral}
        totalCredit={credit?.non_food_credit_cr}
        onInspectEvidence={() => openEvidence(credit?.citation, 'Sectoral Deployment of Credit', formatLakhCr(credit?.non_food_credit_cr), credit?.period)}
      />

      {/* RBI DBIE Official Banking & Credit Telemetry Tables & Charts */}
      {data?.rbi_dbie_live?.sector_tables?.['finance'] && (
        <SectorDbieTableWidget
          sectorKey="finance"
          sectorName="Finance & Banking"
          tables={data.rbi_dbie_live.sector_tables['finance']}
          openEvidence={openEvidence}
          accentColor="cyan"
        />
      )}
    </div>
  );
};
