import React, { useEffect, useRef, useState, useMemo } from 'react';
import {
  Landmark,
  ShieldCheck,
  RefreshCw,
  Search,
  Server,
  Layers,
  TrendingUp,
  Globe,
  Activity,
  Briefcase,
  MapPin,
  Database,
} from 'lucide-react';
import { DashboardOverview, CitationItem } from '../types';
import { useGsapPage } from '../hooks/useGsapPage';
import { TimeSeriesDataPoint } from './charts/TimeSeriesChart';
import { CommandPalette } from './CommandPalette';
import { EvidenceDrawer } from './EvidenceDrawer';

// Tab Views
import { AllSectorsTabView } from './tabs/AllSectorsTabView';
import { FinanceTabView } from './tabs/FinanceTabView';
import { FiscalTabView } from './tabs/FiscalTabView';
import { ExternalTabView } from './tabs/ExternalTabView';
import { MarketsTabView } from './tabs/MarketsTabView';
import { RealLabourTabView } from './tabs/RealLabourTabView';
import { StatesTabView } from './tabs/StatesTabView';
import { DbieTabView } from './tabs/DbieTabView';

const SECTOR_TABS = [
  { key: 'all', label: 'All Sectors Intelligence', icon: Layers },
  { key: 'finance', label: 'Finance & Banking', icon: Landmark },
  { key: 'fiscal', label: 'Fiscal & Union Budget', icon: TrendingUp },
  { key: 'external', label: 'External & Forex', icon: Globe },
  { key: 'markets', label: 'Capital Markets & Rates', icon: Activity },
  { key: 'real_labour', label: 'Real Sector & Labour', icon: Briefcase },
  { key: 'states', label: 'State Finances & GSDP', icon: MapPin },
  { key: 'dbie', label: 'RBI DBIE Live Explorer', icon: Database },
] as const;

type SectorTabKey = (typeof SECTOR_TABS)[number]['key'];

export const DashboardView: React.FC = () => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSectorTab, setActiveSectorTab] = useState<SectorTabKey>('all');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [evidenceDrawerState, setEvidenceDrawerState] = useState<{
    isOpen: boolean;
    citation: CitationItem | null;
    indicatorName?: string;
    currentValue?: string | number | null;
    period?: string | null;
  }>({
    isOpen: false,
    citation: null,
  });

  const [autoRetryCountdown, setAutoRetryCountdown] = useState<number | null>(null);

  const rootRef = useRef<HTMLDivElement>(null);
  useGsapPage(rootRef, [loading, activeSectorTab]);

  // Global Keyboard shortcuts: Cmd+K, Ctrl+K, Cmd+F
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'f')) {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchDashboardData = async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setAutoRetryCountdown(null);
    try {
      const res = await fetch('/api/v1/dashboard/overview', { signal });
      if (!res.ok) {
        if (res.status === 500) {
          throw new Error('HTTP 500: Gateway Connection Refused. The backend server at 127.0.0.1:8000 is unreachable.');
        }
        throw new Error(`HTTP ${res.status}: Failed to load dashboard telemetry`);
      }
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      const msg = err.message || 'Error loading dashboard metrics';
      setError(msg);
      // Start auto-reconnect timer if disconnected
      setAutoRetryCountdown(5);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboardData(controller.signal);
    return () => controller.abort();
  }, []);

  // Countdown timer for auto-retry
  useEffect(() => {
    if (autoRetryCountdown === null) return;
    if (autoRetryCountdown <= 0) {
      fetchDashboardData();
      return;
    }
    const timer = setTimeout(() => {
      setAutoRetryCountdown((prev) => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => clearTimeout(timer);
  }, [autoRetryCountdown]);

  const formatLakhCr = (val?: number | null) => {
    if (val == null) return '—';
    return `₹${(val / 100000).toFixed(2)} L Cr`;
  };

  const formatPct = (val?: number | null, suffix = '%') => {
    if (val == null) return '—';
    return `${val.toFixed(2)}${suffix}`;
  };

  const openEvidence = (
    citation: CitationItem | null | undefined,
    indicatorName: string,
    currentValue?: string | number | null,
    period?: string | null
  ) => {
    setEvidenceDrawerState({
      isOpen: true,
      citation: citation || null,
      indicatorName,
      currentValue,
      period,
    });
  };

  const credit = data?.finance_sector?.credit_growth;
  const fiscal = data?.fiscal_sector;

  // Chart data mappings
  const creditChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.credit) return [];
    return data.timeseries.credit.map((pt) => ({
      period: pt.period,
      value: pt.non_food_credit_cr ? Number((pt.non_food_credit_cr / 100000).toFixed(2)) : 0,
      secondaryValue: pt.non_food_credit_yoy_pct,
      label: 'Non-Food Credit',
    }));
  }, [data]);

  const ratesChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!data?.timeseries?.lending_rates) return [];
    return data.timeseries.lending_rates.map((pt) => ({
      period: pt.period,
      value: pt.walr_fresh_pct,
      secondaryValue: pt.wadtdr_fresh_pct,
      label: 'Fresh WALR',
    }));
  }, [data]);

  const gstChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!fiscal?.gst_history) return [];
    return fiscal.gst_history.map((pt) => ({
      period: pt.period,
      value: Number((pt.gross_gst_cr / 100000).toFixed(2)),
      secondaryValue: pt.yoy_growth_pct,
      label: 'Gross GST Collections',
    }));
  }, [fiscal]);

  return (
    <div
      ref={rootRef}
      className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 space-y-6 md:space-y-8 bg-background selection:bg-brand-500/30 selection:text-cyan-200"
    >
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 shadow-md">
            <Landmark className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Macroeconomic Intelligence Workspace
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Mesh Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-sector intelligence ingested from RBI DBIE, Union Budget 2025-26, MoSPI PLFS, and Indian Data Project open feeds.
            </p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2.5 self-start md:self-auto">
          {/* Quick Search trigger [ ⌘ F ] */}
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-900/80 border border-white/10 hover:border-cyan-400/40 text-xs text-slate-400 hover:text-white transition-all shadow-sm group"
            aria-label="Search dashboard"
          >
            <Search className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline">Search indicators…</span>
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-white/5 border border-white/10 rounded text-slate-400">
              ⌘F
            </kbd>
          </button>

          {/* Sync Live Button */}
          <button
            onClick={() => fetchDashboardData()}
            disabled={loading}
            aria-label="Sync live mirrors"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900/80 border border-white/10 hover:border-cyan-400/40 text-xs font-mono font-semibold text-slate-300 hover:text-white transition-all shadow-sm disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Sync Mirrors</span>
          </button>

          {/* Evidence Inspector Action */}
          <button
            onClick={() => openEvidence(credit?.citation, 'Non-Food Bank Credit', formatLakhCr(credit?.non_food_credit_cr), credit?.period)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/25 text-xs font-mono font-semibold text-cyan-300 transition-all shadow-sm"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Audit Trail</span>
          </button>
        </div>
      </div>

      {/* Real-time Market & Policy Ticker Bar */}
      <div className="p-3 rounded-2xl bg-slate-900/40 border border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-400">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-slate-300">RBI Repo:</span>
            <strong className="text-white">6.50%</strong>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">Neutral</span>
          </div>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300">10-Yr G-Sec:</span>
            <strong className="text-indigo-300">6.77%</strong>
          </div>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300">USD/INR:</span>
            <strong className="text-amber-300">₹85.57</strong>
          </div>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300">SCB Gross NPA:</span>
            <strong className="text-cyan-300">2.80%</strong>
            <span className="text-[10px] text-slate-500">(12-Yr Low)</span>
          </div>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300">Forex Reserves:</span>
            <strong className="text-emerald-400">$700.2 Bn</strong>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-500">
            Active Data Feeds: <code className="text-cyan-300">8 Sectors + Open Data</code>
          </span>
        </div>
      </div>

      {/* Offline / HTTP 500 Connection Diagnostic Alert */}
      {error && (
        <div role="alert" className="p-5 rounded-2xl bg-rose-500/10 border border-rose-500/25 text-rose-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
          <div className="flex items-start gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 shrink-0">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <div className="font-semibold text-rose-300 font-mono text-sm">Backend Gateway Offline</div>
              <p className="mt-1 text-rose-200/90 leading-relaxed font-sans">{error}</p>
            </div>
          </div>
          <button
            onClick={() => fetchDashboardData()}
            className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white font-mono font-semibold text-xs transition-colors shrink-0 flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Gateway Connection
          </button>
        </div>
      )}

      {/* Sector Perspective Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-white/5 scrollbar-none">
        {SECTOR_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSectorTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveSectorTab(tab.key)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono font-medium transition-all shrink-0 ${
                isActive
                  ? 'bg-brand-500/20 text-cyan-300 border border-brand-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab-Specific Workspaces (Dynamic Rendering) */}
      <div className="transition-all duration-300">
        {activeSectorTab === 'all' && (
          <AllSectorsTabView
            data={data}
            openEvidence={openEvidence}
            formatLakhCr={formatLakhCr}
            formatPct={formatPct}
          />
        )}

        {activeSectorTab === 'finance' && (
          <FinanceTabView
            data={data}
            creditChartData={creditChartData}
            ratesChartData={ratesChartData}
            openEvidence={openEvidence}
            formatLakhCr={formatLakhCr}
            formatPct={formatPct}
          />
        )}

        {activeSectorTab === 'fiscal' && (
          <FiscalTabView
            data={data}
            gstChartData={gstChartData}
            openEvidence={openEvidence}
          />
        )}

        {activeSectorTab === 'external' && (
          <ExternalTabView
            data={data}
            openEvidence={openEvidence}
          />
        )}

        {activeSectorTab === 'markets' && (
          <MarketsTabView
            data={data}
            openEvidence={openEvidence}
          />
        )}

        {activeSectorTab === 'real_labour' && (
          <RealLabourTabView
            data={data}
            openEvidence={openEvidence}
          />
        )}

        {activeSectorTab === 'states' && (
          <StatesTabView
            data={data}
            openEvidence={openEvidence}
          />
        )}

        {activeSectorTab === 'dbie' && (
          <DbieTabView
            data={data}
            openEvidence={openEvidence}
          />
        )}
      </div>

      {/* Evidence Drawer for Audit Chains */}
      <EvidenceDrawer
        isOpen={evidenceDrawerState.isOpen}
        onClose={() => setEvidenceDrawerState((prev) => ({ ...prev, isOpen: false }))}
        citation={evidenceDrawerState.citation}
        indicatorName={evidenceDrawerState.indicatorName}
        currentValue={evidenceDrawerState.currentValue}
        period={evidenceDrawerState.period}
      />

      {/* Command Palette for Quick Search */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectSector={(sector: string) => {
          if (['all', 'finance', 'fiscal', 'external', 'markets', 'real_labour', 'states', 'dbie'].includes(sector)) {
            setActiveSectorTab(sector as SectorTabKey);
          }
        }}
        onTriggerSync={() => fetchDashboardData()}
        onOpenEvidence={() => {
          openEvidence(credit?.citation, 'Non-Food Bank Credit', formatLakhCr(credit?.non_food_credit_cr), credit?.period);
        }}
      />
    </div>
  );
};
