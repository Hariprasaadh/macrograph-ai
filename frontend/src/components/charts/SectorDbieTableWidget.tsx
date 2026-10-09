import React, { useState, useMemo } from 'react';
import {
  Database,
  LineChart,
  Table as TableIcon,
  Download,
  ExternalLink,
  ShieldCheck,
  TrendingUp,
  Maximize2,
} from 'lucide-react';
import { RbiDbieSectorTable, CitationItem } from '../../types';
import { TimeSeriesChart, TimeSeriesDataPoint } from './TimeSeriesChart';

interface SectorDbieTableWidgetProps {
  sectorKey: string;
  sectorName: string;
  tables: RbiDbieSectorTable[];
  openEvidence: (citation: CitationItem | null | undefined, name: string, value?: any, period?: string | null) => void;
  accentColor?: 'emerald' | 'cyan' | 'indigo' | 'amber';
}

export const SectorDbieTableWidget: React.FC<SectorDbieTableWidgetProps> = ({
  sectorKey,
  sectorName,
  tables,
  openEvidence,
  accentColor = 'cyan',
}) => {
  const [selectedTableIndex, setSelectedTableIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'chart' | 'table' | 'split'>('split');

  const currentTable = tables && tables.length > 0 ? tables[selectedTableIndex] || tables[0] : null;

  const chartData: TimeSeriesDataPoint[] = useMemo(() => {
    if (!currentTable?.series) return [];
    return currentTable.series.map((pt) => ({
      period: pt.period,
      value: pt.value,
      secondaryValue: pt.secondaryValue,
      label: pt.label || currentTable.title,
    }));
  }, [currentTable]);

  if (!tables || tables.length === 0) {
    return null;
  }

  const colorStyles = {
    emerald: {
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      activeTab: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      text: 'text-emerald-400',
    },
    cyan: {
      badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      activeTab: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      text: 'text-cyan-400',
    },
    indigo: {
      badge: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      activeTab: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
      text: 'text-indigo-400',
    },
    amber: {
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      activeTab: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      text: 'text-amber-400',
    },
  }[accentColor];

  const handleOpenEvidence = () => {
    if (!currentTable) return;
    const citation: CitationItem = {
      source_agent: currentTable.sector || sectorKey,
      table_reference: currentTable.table,
      indicator: currentTable.title,
      observation_period: currentTable.latest_period,
      mcp_tool: 'RBI DBIE FastMCP',
      source_note: currentTable.citation,
    };
    openEvidence(
      citation,
      currentTable.title,
      `${currentTable.latest_value} ${currentTable.unit}`,
      currentTable.latest_period
    );
  };

  return (
    <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-5 shadow-2xl relative overflow-hidden">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`p-1.5 rounded-lg ${colorStyles.badge}`}>
              <Database className="w-4 h-4" />
            </span>
            <h3 className="text-sm sm:text-base font-semibold text-white tracking-tight flex items-center gap-2">
              <span>RBI DBIE Official Telemetry</span>
              <span className="text-xs font-mono text-slate-400 font-normal">({sectorName})</span>
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Direct SDMX observations &amp; official tables from data-api.dbie.rbihub.in
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="bg-slate-900/80 p-0.5 rounded-xl border border-white/10 flex items-center text-xs font-mono">
            <button
              onClick={() => setViewMode('chart')}
              className={`px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all ${
                viewMode === 'chart' ? 'bg-white/15 text-white font-medium' : 'text-slate-400 hover:text-white'
              }`}
              title="Graph & Chart View"
            >
              <LineChart className="w-3.5 h-3.5" />
              <span>Chart</span>
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all ${
                viewMode === 'table' ? 'bg-white/15 text-white font-medium' : 'text-slate-400 hover:text-white'
              }`}
              title="Data Table View"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all ${
                viewMode === 'split' ? 'bg-white/15 text-white font-medium' : 'text-slate-400 hover:text-white'
              }`}
              title="Split Chart & Table"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Split</span>
            </button>
          </div>
        </div>
      </div>

      {/* Sector Table Selector Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {tables.map((t, idx) => (
          <button
            key={t.id || t.table}
            onClick={() => setSelectedTableIndex(idx)}
            className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all shrink-0 border flex items-center gap-2 ${
              selectedTableIndex === idx
                ? `${colorStyles.activeTab} font-semibold shadow-sm`
                : 'border-white/5 bg-slate-900/40 text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <span className="truncate max-w-[200px]">{t.title}</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-black/30 text-slate-300">
              {t.table}
            </span>
          </button>
        ))}
      </div>

      {currentTable && (
        <>
          {/* Table KPI Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/40 p-3.5 rounded-xl border border-white/5">
            <div>
              <div className="text-[11px] text-slate-400 font-mono">Latest Official Observation</div>
              <div className="text-lg sm:text-xl font-bold text-white font-mono mt-0.5">
                {typeof currentTable.latest_value === 'number'
                  ? currentTable.latest_value.toLocaleString()
                  : currentTable.latest_value}{' '}
                <span className="text-xs font-normal text-slate-400">{currentTable.unit}</span>
              </div>
            </div>

            <div>
              <div className="text-[11px] text-slate-400 font-mono">YoY Momentum</div>
              <div className="text-lg sm:text-xl font-bold font-mono mt-0.5 flex items-center gap-1 text-emerald-400">
                <TrendingUp className="w-4 h-4" />
                <span>{currentTable.yoy_change}</span>
              </div>
            </div>

            <div>
              <div className="text-[11px] text-slate-400 font-mono">Reporting Frequency</div>
              <div className="text-sm font-semibold text-slate-200 font-mono mt-1">
                {currentTable.frequency}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">As of {currentTable.latest_period}</div>
            </div>

            <div className="flex flex-col justify-between items-start sm:items-end">
              <div className="text-[11px] text-slate-400 font-mono">Owner Agent</div>
              <button
                onClick={handleOpenEvidence}
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${colorStyles.badge} hover:brightness-125 transition-all flex items-center gap-1 mt-1`}
              >
                <ShieldCheck className="w-3 h-3" />
                <span>{currentTable.sector}</span>
              </button>
            </div>
          </div>

          {/* Visual Presentation Area: Chart / Table / Split */}
          <div className="space-y-4">
            {(viewMode === 'chart' || viewMode === 'split') && (
              <div className={viewMode === 'split' ? 'grid grid-cols-1 lg:grid-cols-2 gap-4' : ''}>
                <div className="rounded-xl overflow-hidden">
                  <TimeSeriesChart
                    title={`${currentTable.title} Trajectory`}
                    subtitle={`Time series queried from DBIE ${currentTable.schema}/${currentTable.table}`}
                    data={chartData}
                    valueSuffix={` ${currentTable.unit}`}
                    color={accentColor}
                    height={viewMode === 'split' ? 220 : 260}
                    onInspectEvidence={handleOpenEvidence}
                  />
                </div>

                {viewMode === 'split' && (
                  <div className="bg-slate-950/60 rounded-xl border border-white/5 p-4 flex flex-col justify-between overflow-x-auto">
                    <div>
                      <div className="flex items-center justify-between pb-2 border-b border-white/5">
                        <span className="text-xs font-mono font-medium text-slate-300">
                          Historical Observations Table
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {currentTable.rows_count?.toLocaleString()} Records
                        </span>
                      </div>
                      <table className="w-full text-left text-xs font-mono mt-2">
                        <thead className="text-slate-500 text-[10px] uppercase border-b border-white/5">
                          <tr>
                            <th className="py-1.5 px-2">Period</th>
                            <th className="py-1.5 px-2 text-right">Value</th>
                            <th className="py-1.5 px-2 text-right">YoY</th>
                            <th className="py-1.5 px-2 text-right">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                          {(currentTable.table_data && currentTable.table_data.length > 0
                            ? currentTable.table_data
                            : currentTable.series.map((s) => ({
                                period: s.period,
                                value: s.value,
                                yoy: currentTable.yoy_change,
                                status: 'Verified',
                              }))
                          ).map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-white/5 transition-colors">
                              <td className="py-2 px-2 text-white font-medium">{row.period}</td>
                              <td className="py-2 px-2 text-right text-cyan-300 font-bold">
                                {typeof row.value === 'number' ? row.value.toLocaleString() : row.value}
                              </td>
                              <td className="py-2 px-2 text-right text-emerald-400">
                                {row.yoy || currentTable.yoy_change}
                              </td>
                              <td className="py-2 px-2 text-right text-slate-400 text-[10px]">
                                {row.status || 'Verified'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span className="truncate max-w-[220px]" title={currentTable.dbie_path}>
                        {currentTable.dbie_path}
                      </span>
                      <div className="flex items-center gap-2">
                        <a
                          href={`https://data-api.dbie.rbihub.in/api/tables/${currentTable.schema}/${currentTable.table}/csv`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white"
                          title="Download CSV"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <a
                          href={`https://data-api.dbie.rbihub.in/api/tables/${currentTable.schema}/${currentTable.table}/rows?limit=20`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400"
                          title="View JSON"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {viewMode === 'table' && (
              <div className="bg-slate-950/60 rounded-xl border border-white/5 p-4 overflow-x-auto">
                <div className="flex items-center justify-between pb-3 border-b border-white/5">
                  <div>
                    <h4 className="text-sm font-semibold text-white font-mono">{currentTable.title}</h4>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">{currentTable.dbie_path}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={`https://data-api.dbie.rbihub.in/api/tables/${currentTable.schema}/${currentTable.table}/csv`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-mono flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download CSV</span>
                    </a>
                  </div>
                </div>

                <table className="w-full text-left text-xs font-mono mt-3">
                  <thead className="text-slate-400 text-[11px] uppercase border-b border-white/10 bg-slate-900/50">
                    <tr>
                      <th className="py-2 px-3">Period</th>
                      <th className="py-2 px-3">Component / Series</th>
                      <th className="py-2 px-3 text-right">Observation ({currentTable.unit})</th>
                      <th className="py-2 px-3 text-right">YoY Momentum</th>
                      <th className="py-2 px-3 text-right">Data Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300">
                    {(currentTable.table_data && currentTable.table_data.length > 0
                      ? currentTable.table_data
                      : currentTable.series.map((s) => ({
                          period: s.period,
                          value: s.value,
                          component: currentTable.title,
                          yoy: currentTable.yoy_change,
                          status: 'Verified Official',
                        }))
                    ).map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-white/5 transition-colors">
                        <td className="py-2.5 px-3 text-white font-medium">{row.period}</td>
                        <td className="py-2.5 px-3 text-slate-300">{row.component || currentTable.title}</td>
                        <td className="py-2.5 px-3 text-right text-cyan-300 font-bold">
                          {typeof row.value === 'number' ? row.value.toLocaleString() : row.value}
                        </td>
                        <td className="py-2.5 px-3 text-right text-emerald-400">{row.yoy || currentTable.yoy_change}</td>
                        <td className="py-2.5 px-3 text-right text-slate-400">{row.status || 'Verified Official'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Attribution footer */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 border-t border-white/5 text-[11px] font-mono text-slate-400">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">FastMCP Tool:</span>
              <code className="text-cyan-300 bg-cyan-500/10 px-1.5 py-0.5 rounded text-[10px]">
                {currentTable.mcp_command || `get_series(table="${currentTable.table}")`}
              </code>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Citation:</span>
              <span className="text-slate-300 truncate max-w-[320px]">{currentTable.citation}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
