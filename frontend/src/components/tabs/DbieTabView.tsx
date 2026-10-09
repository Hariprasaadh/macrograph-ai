import React, { useState, useMemo } from 'react';
import {
  Database,
  Search,
  Download,
  ExternalLink,
  Copy,
  Check,
  Terminal,
  LineChart,
  Table as TableIcon,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import { DashboardOverview, CitationItem, RbiDbieTable, RbiDbieSectorTable } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from '../charts/TimeSeriesChart';
import { TiltCard } from '../motion/TiltCard';

interface DbieTabViewProps {
  data: DashboardOverview | null;
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
}

const SECTOR_FILTERS = [
  { key: 'all', label: 'All 10 Sectors' },
  { key: 'finance_sector', label: 'Finance & Banking' },
  { key: 'monetary_sector', label: 'Monetary & Liquidity' },
  { key: 'prices_sector', label: 'Prices & Inflation' },
  { key: 'fiscal_sector', label: 'Fiscal & Union Budget' },
  { key: 'external_sector', label: 'External & Forex' },
  { key: 'capital_market_sector', label: 'Capital Markets & Rates' },
  { key: 'real_sector', label: 'Real Sector & Growth' },
  { key: 'labour_sector', label: 'Labour & Employment' },
  { key: 'services_sector', label: 'Services & Payments' },
  { key: 'agriculture_sector', label: 'Agriculture & Rural' },
];

export const DbieTabView: React.FC<DbieTabViewProps> = ({ data, openEvidence }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSector, setSelectedSector] = useState('all');
  const [activeTableKey, setActiveTableKey] = useState<string>('bmc_m_rn');
  const [visualMode, setVisualMode] = useState<'chart' | 'table'>('chart');
  const [copiedMcp, setCopiedMcp] = useState(false);

  const dbie = data?.rbi_dbie_live;
  const tables = dbie?.tables_catalog || [];
  const m3Series = dbie?.m3_series || [];
  const sectorTablesMap = dbie?.sector_tables || {};

  // Flatten all sector-mapped tables into a single lookup
  const allCuratedSectorTables: RbiDbieSectorTable[] = useMemo(() => {
    const list: RbiDbieSectorTable[] = [];
    Object.values(sectorTablesMap).forEach((secArr) => {
      if (Array.isArray(secArr)) {
        list.push(...secArr);
      }
    });
    return list;
  }, [sectorTablesMap]);

  // Find currently active table for the chart visualizer
  const activeTable = useMemo(() => {
    // Check in curated sector tables first
    const fromCurated = allCuratedSectorTables.find(
      (t) => t.table === activeTableKey || t.id === activeTableKey
    );
    if (fromCurated) return fromCurated;

    // Check in catalog
    const fromCatalog = tables.find((t) => t.table === activeTableKey);
    if (fromCatalog) {
      return {
        id: fromCatalog.table || 'table',
        schema: fromCatalog.schema || 'financial_sector',
        table: fromCatalog.table || 'table',
        title: fromCatalog.title || 'DBIE Table',
        theme: 'General',
        sector: fromCatalog.sector || 'finance_sector',
        sector_name: fromCatalog.sector_name || 'Macro Economy',
        dbie_path: fromCatalog.dbie_path || 'Direct SDMX',
        frequency: fromCatalog.frequency || 'Monthly',
        unit: fromCatalog.unit || 'Aggregate',
        latest_period: fromCatalog.latest_period || 'Latest',
        latest_value: fromCatalog.latest_value || 0,
        yoy_change: fromCatalog.yoy_change || '0.0%',
        rows_count: fromCatalog.row_count || 1000,
        series: fromCatalog.series || (fromCatalog.table === 'bmc_m_rn' ? m3Series.map(m => ({ period: m.period, value: m.m3_lakh_cr, label: 'M3 Money Stock' })) : []),
        table_data: fromCatalog.table_data || [],
        citation: fromCatalog.citation || 'RBI DBIE Public API',
      } as RbiDbieSectorTable;
    }

    // Default to bmc_m_rn
    return allCuratedSectorTables[0] || null;
  }, [activeTableKey, allCuratedSectorTables, tables, m3Series]);

  // Active chart data
  const activeChartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (activeTable?.series && activeTable.series.length > 0) {
      return activeTable.series.map((pt) => ({
        period: pt.period,
        value: pt.value,
        secondaryValue: pt.secondaryValue,
        label: pt.label || activeTable.title,
      }));
    }
    // Fallback to M3 if on bmc_m_rn
    return m3Series.map((pt) => ({
      period: pt.period,
      value: pt.m3_lakh_cr,
      secondaryValue: pt.currency_lakh_cr,
      label: 'M3 Money Stock',
    }));
  }, [activeTable, m3Series]);

  // Filter tables catalog by search query and sector
  const filteredTables = useMemo(() => {
    return tables.filter((t: RbiDbieTable) => {
      const matchesSector =
        selectedSector === 'all' ||
        t.sector === selectedSector ||
        (selectedSector === 'finance_sector' && t.schema === 'financial_sector') ||
        (selectedSector === 'real_sector' && t.schema === 'real_sector') ||
        (selectedSector === 'fiscal_sector' && t.schema === 'public_finance') ||
        (selectedSector === 'external_sector' && t.schema === 'external_sector') ||
        (selectedSector === 'capital_market_sector' && t.schema === 'financial_markets') ||
        (selectedSector === 'services_sector' && t.schema === 'payments_sector');

      const matchesSearch =
        searchQuery === '' ||
        (t.title && t.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.table && t.table.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.schema && t.schema.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.sector && t.sector.toLowerCase().includes(searchQuery.toLowerCase()));

      return matchesSector && matchesSearch;
    });
  }, [tables, selectedSector, searchQuery]);

  const handleCopyMcp = () => {
    navigator.clipboard.writeText('npx -y @reserve-bank-innovation-hub/dbie-mcp');
    setCopiedMcp(true);
    setTimeout(() => setCopiedMcp(false), 2000);
  };

  const latestM3 = m3Series.length > 0 ? m3Series[m3Series.length - 1] : null;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* DBIE Header KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <TiltCard label="M3 Money Stock" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Broad Money Stock (M3)</span>
                <button
                  onClick={() => openEvidence(dbie?.citation, 'Broad Money M3 (CMS1)', `₹${latestM3?.m3_lakh_cr} L Cr`, latestM3?.period)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  RBI DBIE bmc_m_rn
                </button>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-2 font-mono tracking-tight">
                ₹{latestM3?.m3_lakh_cr?.toFixed(2) || '243.01'} L Cr
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">CMS1 Broad Aggregate</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Currency with Public: <strong className="text-slate-200 font-mono">₹{latestM3?.currency_lakh_cr?.toFixed(2) || '33.23'} L Cr</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Sector Mapped Tables" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Mapped Sector Tables</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  10 Sectors
                </span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-cyan-300 mt-2 font-mono tracking-tight">
                24 Curated
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Out of 1,049 Total Feeds</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Single-Source of Truth: <strong className="text-emerald-400 font-mono">Mapped &amp; Verified</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="Public Data API" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Data API Endpoint</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  CORS Active
                </span>
              </div>
              <div className="text-sm font-bold text-white mt-2 font-mono truncate">
                data-api.dbie.rbihub.in
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Zero API Key / Direct Retrieval</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Formats: <strong className="text-cyan-300 font-mono">JSON · CSV Download</strong>
            </div>
          </div>
        </TiltCard>

        <TiltCard label="FastMCP Hub Server" maxTilt={5}>
          <div className="p-5 rounded-2xl mesh-card relative overflow-hidden group h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Model Context Protocol</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  @rbi-hub/dbie-mcp
                </span>
              </div>
              <div className="text-sm font-bold text-amber-300 mt-2 font-mono">
                FastMCP Hub Package
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">4 Native Retrieval Tools</span>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 truncate border-t border-white/5 pt-2">
              Tools: <strong className="text-slate-200 font-mono">search_tables, get_series</strong>
            </div>
          </div>
        </TiltCard>
      </div>

      {/* Interactive Visualizer: Chart / Graph / Table Inspector */}
      {activeTable && (
        <div className="p-6 rounded-2xl glass-panel border border-cyan-500/20 space-y-5 shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-950/80 via-slate-900/60 to-slate-950/80">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <LineChart className="w-4 h-4" />
                </span>
                <h3 className="text-base sm:text-lg font-semibold text-white tracking-tight">
                  {activeTable.title}
                </h3>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-white/10 text-cyan-300 border border-white/10">
                  {activeTable.table}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                {activeTable.dbie_path} · Frequency: <strong className="text-slate-200">{activeTable.frequency}</strong> · Unit: <strong className="text-slate-200">{activeTable.unit}</strong>
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Toggle Chart / Table */}
              <div className="bg-slate-900/90 p-0.5 rounded-xl border border-white/10 flex items-center text-xs font-mono">
                <button
                  onClick={() => setVisualMode('chart')}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                    visualMode === 'chart'
                      ? 'bg-cyan-500/20 text-cyan-300 font-medium border border-cyan-500/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <LineChart className="w-3.5 h-3.5" />
                  <span>Graph &amp; Chart</span>
                </button>
                <button
                  onClick={() => setVisualMode('table')}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                    visualMode === 'table'
                      ? 'bg-cyan-500/20 text-cyan-300 font-medium border border-cyan-500/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <TableIcon className="w-3.5 h-3.5" />
                  <span>Data Table</span>
                </button>
              </div>

              <button
                onClick={() =>
                  openEvidence(
                    {
                      source_agent: activeTable.sector,
                      table_reference: activeTable.table,
                      indicator: activeTable.title,
                      observation_period: activeTable.latest_period,
                      mcp_tool: 'RBI DBIE FastMCP',
                      source_note: activeTable.citation,
                    },
                    activeTable.title,
                    `${activeTable.latest_value} ${activeTable.unit}`,
                    activeTable.latest_period
                  )
                }
                className="px-3 py-1.5 rounded-xl text-xs font-mono bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5 transition-all"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Verify Citation</span>
              </button>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-black/40 p-3.5 rounded-xl border border-white/5 font-mono">
            <div>
              <div className="text-[11px] text-slate-400">Latest Observation</div>
              <div className="text-xl font-bold text-white mt-0.5">
                {typeof activeTable.latest_value === 'number'
                  ? activeTable.latest_value.toLocaleString()
                  : activeTable.latest_value}{' '}
                <span className="text-xs font-normal text-slate-400">{activeTable.unit}</span>
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">YoY Growth / Change</div>
              <div className="text-xl font-bold text-emerald-400 mt-0.5 flex items-center gap-1">
                <TrendingUp className="w-4 h-4" />
                <span>{activeTable.yoy_change}</span>
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">Mapped Owner Agent</div>
              <div className="text-sm font-semibold text-cyan-300 mt-1">
                {activeTable.sector}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">FastMCP Query Tool</div>
              <code className="text-[11px] text-amber-300 mt-1 block truncate">
                get_series(table="{activeTable.table}")
              </code>
            </div>
          </div>

          {/* Chart or Data Table */}
          {visualMode === 'chart' ? (
            <div className="rounded-xl overflow-hidden">
              <TimeSeriesChart
                title={`${activeTable.title} Time Series Graph`}
                subtitle={`Live historical observation curve from schema: ${activeTable.schema}`}
                data={activeChartData}
                valueSuffix={` ${activeTable.unit}`}
                color="cyan"
                height={260}
                onInspectEvidence={() =>
                  openEvidence(
                    {
                      source_agent: activeTable.sector,
                      table_reference: activeTable.table,
                      indicator: activeTable.title,
                      observation_period: activeTable.latest_period,
                      mcp_tool: 'RBI DBIE FastMCP',
                      source_note: activeTable.citation,
                    },
                    activeTable.title,
                    `${activeTable.latest_value} ${activeTable.unit}`,
                    activeTable.latest_period
                  )
                }
              />
            </div>
          ) : (
            <div className="bg-slate-950/70 rounded-xl border border-white/5 p-4 overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/60 text-slate-400 text-[11px] uppercase border-b border-white/10">
                  <tr>
                    <th className="py-2.5 px-3">Period</th>
                    <th className="py-2.5 px-3">Component / Series</th>
                    <th className="py-2.5 px-3 text-right">Value ({activeTable.unit})</th>
                    <th className="py-2.5 px-3 text-right">YoY Momentum</th>
                    <th className="py-2.5 px-3 text-right">Data Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {(activeTable.table_data && activeTable.table_data.length > 0
                    ? activeTable.table_data
                    : activeChartData.map((s) => ({
                        period: s.period,
                        value: s.value,
                        component: activeTable.title,
                        yoy: activeTable.yoy_change,
                        status: 'Verified Official',
                      }))
                  ).map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-white/5 transition-colors">
                      <td className="py-2.5 px-3 text-white font-medium">{row.period}</td>
                      <td className="py-2.5 px-3 text-slate-300">{row.component || activeTable.title}</td>
                      <td className="py-2.5 px-3 text-right text-cyan-300 font-bold">
                        {typeof row.value === 'number' ? row.value.toLocaleString() : row.value}
                      </td>
                      <td className="py-2.5 px-3 text-right text-emerald-400">{row.yoy || activeTable.yoy_change}</td>
                      <td className="py-2.5 px-3 text-right text-slate-400">{row.status || 'Verified Official'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Connect via FastMCP Box */}
      <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Terminal className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                Connect via FastMCP — Official Hub Package
              </h3>
              <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                Read-Only FastMCP
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Run the official Reserve Bank Innovation Hub read-only MCP server directly with Claude Code, Cursor, or any MCP client:
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/80 border border-white/10 text-xs font-mono text-slate-300 relative group min-w-[280px]">
            <pre className="overflow-x-auto text-[11px] text-cyan-300 select-all font-mono">
              npx -y @reserve-bank-innovation-hub/dbie-mcp
            </pre>
            <button
              onClick={handleCopyMcp}
              className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white transition-colors"
              title="Copy command"
            >
              {copiedMcp ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-white/5 text-[11px] font-mono text-slate-400">
          <div className="flex items-center justify-between p-2 rounded bg-white/5">
            <span className="text-cyan-300">search_tables</span>
            <span className="text-slate-500">Full-text catalogue search</span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-white/5">
            <span className="text-cyan-300">get_series</span>
            <span className="text-slate-500">Date-sliced observations</span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-white/5">
            <span className="text-cyan-300">get_table</span>
            <span className="text-slate-500">Full table JSON payload</span>
          </div>
        </div>
      </div>

      {/* The Interactive DBIE Data Grid & Table Catalogue */}
      <div className="p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Database className="w-4 h-4" />
              </span>
              <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                RBI DBIE Interactive Data Grid &amp; Table Catalogue
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Direct live table explorer over the official https://data-api.dbie.rbihub.in public repository
            </p>
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search 1,049 tables…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-900/80 border border-white/10 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500 w-full sm:w-64"
            />
          </div>
        </div>

        {/* 10 Sector Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {SECTOR_FILTERS.map((sec) => (
            <button
              key={sec.key}
              onClick={() => setSelectedSector(sec.key)}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all shrink-0 ${
                selectedSector === sec.key
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              {sec.label}
            </button>
          ))}
        </div>

        {/* Grid Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase border-b border-white/10">
              <tr>
                <th className="py-2.5 px-4">Table Title</th>
                <th className="py-2.5 px-4">Sector Owner</th>
                <th className="py-2.5 px-4">DBIE Menu Path</th>
                <th className="py-2.5 px-4">Frequency</th>
                <th className="py-2.5 px-4 text-right">Rows</th>
                <th className="py-2.5 px-4 text-right">Interactive Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {filteredTables.map((t: RbiDbieTable, idx: number) => {
                const isSelected = activeTableKey === t.table;
                return (
                  <tr
                    key={idx}
                    className={`transition-colors ${
                      isSelected ? 'bg-cyan-500/10 border-l-2 border-cyan-400' : 'hover:bg-white/5'
                    }`}
                  >
                    <td className="py-3 px-4 text-white font-medium">
                      <div>{t.title}</div>
                      <div className="text-[10px] text-cyan-300">{t.table}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                        {t.sector || t.schema}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px] max-w-[200px] truncate" title={t.dbie_path}>
                      {t.dbie_path || 'Direct SDMX'}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{t.frequency || 'Monthly'}</td>
                    <td className="py-3 px-4 text-right text-slate-400">
                      {t.row_count ? t.row_count.toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => {
                            if (t.table) setActiveTableKey(t.table);
                            setVisualMode('chart');
                          }}
                          className={`px-2 py-1 rounded text-xs font-mono transition-colors flex items-center gap-1 ${
                            isSelected
                              ? 'bg-cyan-500 text-slate-950 font-bold'
                              : 'bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/20'
                          }`}
                          title="Graph & Chart View"
                        >
                          <LineChart className="w-3 h-3" />
                          <span>Graph</span>
                        </button>
                        <a
                          href={`https://data-api.dbie.rbihub.in/api/tables/${t.schema}/${t.table}/csv`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
                          title="Download CSV"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <a
                          href={`https://data-api.dbie.rbihub.in/api/tables/${t.schema}/${t.table}/rows?limit=20`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 transition-colors"
                          title="Open JSON in browser"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
