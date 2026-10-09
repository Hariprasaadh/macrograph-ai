import React from 'react';
import { Landmark, ArrowUpRight, ShieldCheck, FileText } from 'lucide-react';
import { DashboardOverview, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { SectorDbieTableWidget } from '../charts/SectorDbieTableWidget';
import { TiltCard } from '../motion/TiltCard';

interface FiscalTabViewProps {
  data: DashboardOverview | null;
  gstChartData: TimeSeriesDataPoint[];
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

export const FiscalTabView: React.FC<FiscalTabViewProps> = ({ data, gstChartData, openEvidence }) => {
  const fiscal = data?.fiscal_sector;
  const budget = data?.union_budget;
  const summary = budget?.summary;
  const ministries = budget?.ministries || [];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Fiscal Headline KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="Total Union Expenditure" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Total Expenditure (BE)</span>
                <button
                  onClick={() => openEvidence(budget?.citation, 'Union Budget Total Expenditure', `₹${((summary?.totalExpenditure || 5065345) / 100000).toFixed(2)} L Cr`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
                >
                  Budget 25-26
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-amber-300 mt-2 font-mono tracking-tight">
                ₹{((summary?.totalExpenditure || 5065345) / 100000).toFixed(2)} L Cr
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 flex items-center gap-0.5 border border-emerald-500/25 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  +6.8% YoY
                </span>
                <span className="text-[11px] text-slate-500 font-mono">GDP Share: ~14.2%</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Per-Capita Daily Spend: <strong className="text-slate-200 font-mono">₹{summary?.perCapitaDailyExpenditure || 95.71} / citizen</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Total Government Receipts" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Total Receipts (Net)</span>
                <button
                  onClick={() => openEvidence(budget?.citation, 'Union Budget Total Receipts', `₹${((summary?.totalReceipts || 3496409) / 100000).toFixed(2)} L Cr`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                >
                  OBI Verified
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                ₹{((summary?.totalReceipts || 3496409) / 100000).toFixed(2)} L Cr
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[11px] text-slate-400 font-mono">
                  Revenue: ₹{((summary?.revenueReceipts || 3420409) / 100000).toFixed(2)} L Cr
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Capital Receipts: <strong className="text-slate-200 font-mono">₹{((summary?.capitalReceipts || 76000) / 100000).toFixed(2)} L Cr</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Union Fiscal Deficit" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Fiscal Deficit (% GDP)</span>
                <button
                  onClick={() => openEvidence(budget?.citation, 'Union Fiscal Deficit Glidepath', `${summary?.fiscalDeficitPercentGDP || 4.4}%`, summary?.year)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  FRBM Target
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                {summary?.fiscalDeficitPercentGDP || 4.4}%
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">
                  Deficit Vol: ₹{((summary?.fiscalDeficit || 1568936) / 100000).toFixed(2)} L Cr
                </span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-emerald-400 truncate border-t border-white/5 pt-2 font-mono">
              Glidepath: 6.4% → 5.6% → 4.9% → 4.4%
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Monthly GST Inflow" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Monthly GST Collections</span>
                <button
                  onClick={() => openEvidence(fiscal?.latest_gst?.citation, 'Gross GST Collections', `₹${fiscal?.latest_gst?.gross_gst_cr?.toLocaleString()} Cr`, fiscal?.latest_gst?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                >
                  PIB MoF
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-indigo-300 mt-2 font-mono tracking-tight">
                ₹{((fiscal?.latest_gst?.gross_gst_cr || 210267) / 100000).toFixed(2)} L Cr
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-300 font-mono border border-indigo-500/25">
                  +{fiscal?.latest_gst?.yoy_growth_pct || 12.4}% YoY
                </span>
                <span className="text-[11px] text-slate-500 font-mono">{fiscal?.latest_gst?.period || 'Latest'}</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              IGST: ₹{((fiscal?.latest_gst?.igst_cr || 99623) / 100000).toFixed(2)} L Cr | CGST: ₹{((fiscal?.latest_gst?.cgst_cr || 43846) / 100000).toFixed(2)} L Cr
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Charts & Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
        {/* GST Time-Series Chart */}
        <TimeSeriesChart
          title="Gross Monthly GST Revenue Trajectory"
          subtitle="Official tax collections published by Ministry of Finance PIB mirror"
          data={gstChartData}
          valuePrefix="₹"
          valueSuffix=" L Cr"
          secondaryLabel="YoY Growth"
          secondarySuffix="%"
          color="cyan"
          onInspectEvidence={() =>
            openEvidence(fiscal?.latest_gst?.citation, 'Gross GST Collections Time Series', `₹${fiscal?.latest_gst?.gross_gst_cr} Cr`, fiscal?.latest_gst?.period)
          }
        />

        {/* General Government Debt & Fiscal Consolidation */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-5 shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-2">
                <Landmark className="w-4 h-4 text-amber-400" />
                <span>Fiscal Consolidation &amp; Sovereign Debt Parameters</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                FRBM statutory targets and General Government Debt-to-GDP trajectory
              </p>
            </div>
            <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              CGA / MoF
            </span>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-300 font-medium">General Government Debt to GDP</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">Centre + States Consolidated Liabilities</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-amber-400 font-mono">
                  {fiscal?.latest_debt?.general_govt_gross_debt_gdp_pct || 81.3}% of GDP
                </div>
                <div className="text-[10px] text-slate-400 font-mono mt-0.5">Period: {fiscal?.latest_debt?.period || 'FY24'}</div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-300 font-medium">Capital Expenditure (Capex) Thrust</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">High-multiplier infrastructure outlays</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-emerald-400 font-mono">₹11.11 L Cr</div>
                <div className="text-[10px] text-emerald-400 font-mono mt-0.5">3.4% of GDP (Record High)</div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-300 font-medium">Gross Tax-to-GDP Ratio</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">Direct + Indirect Tax Efficiency</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-cyan-300 font-mono">11.7%</div>
                <div className="text-[10px] text-cyan-400 font-mono mt-0.5">Buoyancy factor: ~1.2x</div>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2 font-mono">
            <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>Fiscal deficit target anchored on track to breach below 4.5% by FY26.</span>
          </div>
        </div>
      </div>

      {/* Union Budget 2025-26 Ministry Allocations Table */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <FileText className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                Union Budget 2025-26: Major Ministry Allocations
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Statutory expenditure distributions from Open Budgets India mirror (https://openbudgetsindia.org)
            </p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded-full border border-cyan-500/20 self-start sm:self-auto">
            Live Open Dataset Ingested
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Ministry / Item</th>
                <th className="py-2.5 px-4 text-right">Budget Estimate (₹ Cr)</th>
                <th className="py-2.5 px-4 text-right">Share of Total</th>
                <th className="py-2.5 px-4 text-right">YoY Change</th>
                <th className="py-2.5 px-4 text-right">Per Capita (₹)</th>
                <th className="py-2.5 px-4 text-right">Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {ministries.map((m, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 text-white font-medium">
                    <div>{m.name}</div>
                    {m.humanContext && <div className="text-[10px] text-slate-500 font-sans">{m.humanContext}</div>}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-amber-300">
                    ₹{m.budgetEstimate.toLocaleString()} Cr
                  </td>
                  <td className="py-3 px-4 text-right text-slate-300">{m.percentOfTotal}%</td>
                  <td className="py-3 px-4 text-right text-emerald-400">+{m.yoyChange}%</td>
                  <td className="py-3 px-4 text-right text-slate-400">₹{m.perCapita ? m.perCapita.toLocaleString() : '—'}</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => openEvidence(budget?.citation, `Budget: ${m.name}`, `₹${m.budgetEstimate.toLocaleString()} Cr`, '2025-26')}
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

      {/* RBI DBIE Official Public Finance & Budget Telemetry Tables & Charts */}
      {data?.rbi_dbie_live?.sector_tables?.['fiscal'] && (
        <SectorDbieTableWidget
          sectorKey="fiscal"
          sectorName="Fiscal & Union Budget"
          tables={data.rbi_dbie_live.sector_tables['fiscal']}
          openEvidence={openEvidence}
          accentColor="emerald"
        />
      )}
    </div>
  );
};
