import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Share2, ArrowRight, Zap, RefreshCw } from 'lucide-react';
import { TiltCard } from './motion/TiltCard';
import { useGsapPage } from '../hooks/useGsapPage';
import type { KgPathResponse, KgImpactsResponse } from '../types';

interface IndicatorOption {
  id: string;
  label: string;
}

// Indicators that participate in at least one causal edge of the ontology.
const INDICATORS: IndicatorOption[] = [
  { id: 'in.macro.prices.brent_crude', label: 'Brent Crude' },
  { id: 'in.macro.prices.wpi_all', label: 'WPI (All Commodities)' },
  { id: 'in.macro.prices.cpi_headline', label: 'Headline CPI' },
  { id: 'in.macro.prices.cpi_food', label: 'Food CPI' },
  { id: 'in.macro.monetary.repo_rate', label: 'Policy Repo Rate' },
  { id: 'in.macro.monetary.bank_credit_growth', label: 'Bank Credit Growth' },
  { id: 'in.macro.real.iip_growth', label: 'IIP Growth' },
  { id: 'in.macro.real.gdp_growth', label: 'Real GDP Growth' },
  { id: 'in.macro.real.gfcf_investment', label: 'Gross Fixed Capital Formation' },
  { id: 'in.macro.fiscal.central_capex', label: 'Central Capex' },
  { id: 'in.macro.external.trade_balance', label: 'Trade Balance' },
  { id: 'in.macro.external.usd_inr', label: 'USD/INR' },
  { id: 'in.macro.capmarkets.bank_nifty', label: 'NIFTY Bank' },
  { id: 'in.macro.agri.monsoon_departure', label: 'Monsoon Departure' },
  { id: 'in.macro.agri.foodgrain_production', label: 'Foodgrain Production' },
];

const shortName = (id: string): string => id.split('.').slice(-1)[0];

export const KnowledgeGraphView: React.FC = () => {
  const [source, setSource] = useState('in.macro.monetary.repo_rate');
  const [target, setTarget] = useState('in.macro.real.gdp_growth');
  const [pathData, setPathData] = useState<KgPathResponse | null>(null);
  const [impactData, setImpactData] = useState<KgImpactsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  useGsapPage(rootRef, [loading]);

  const fetchCausalData = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const [pRes, iRes] = await Promise.all([
        fetch(
          `/api/v1/kg/path?source_id=${encodeURIComponent(source)}&target_id=${encodeURIComponent(target)}`,
          { signal: controller.signal },
        ),
        fetch(`/api/v1/kg/impacts?shock_id=${encodeURIComponent(source)}`, { signal: controller.signal }),
      ]);
      if (!pRes.ok || !iRes.ok) {
        throw new Error(`Knowledge graph request failed (${pRes.status}/${iRes.status})`);
      }
      setPathData((await pRes.json()) as KgPathResponse);
      setImpactData((await iRes.json()) as KgImpactsResponse);
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return;
      setError(e instanceof Error ? e.message : 'Knowledge graph request failed');
    } finally {
      if (abortRef.current === controller) setLoading(false);
    }
  }, [source, target]);

  useEffect(() => {
    void fetchCausalData();
    return () => abortRef.current?.abort();
  }, [fetchCausalData]);

  return (
    <div ref={rootRef} className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-background">
      <div data-entrance className="pb-6 border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              NetworkX Causal Engine
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400 font-mono">Transmission Channels</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Cross-Sector Causal Transmission Graph
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Map impulse-response lag months and transmission channels between macro indicators.
          </p>
        </div>

        <button
          onClick={() => void fetchCausalData()}
          disabled={loading}
          aria-label="Refresh transmission traversal"
          className="touch-44 flex items-center gap-2 px-3.5 py-2 rounded-xl glass-panel hover:bg-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-all self-start md:self-auto disabled:opacity-60"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Traversal</span>
        </button>
      </div>

      {/* Interactive Transmission Query Form */}
      <div className="p-5 rounded-2xl glass-panel border border-white/10 space-y-4">
        <h3 className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-semibold flex items-center gap-2">
          <Zap className="w-4 h-4" />
          <span>Transmission Path Query</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="kg-source" className="block text-xs font-medium text-slate-300 mb-1.5">Source Shock Indicator</label>
            <select
              id="kg-source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="touch-44 w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-white/10 text-white font-mono focus:outline-none focus:border-cyan-500"
            >
              {INDICATORS.map((ind) => (
                <option key={ind.id} value={ind.id}>{ind.id} ({ind.label})</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="kg-target" className="block text-xs font-medium text-slate-300 mb-1.5">Target Response Indicator</label>
            <select
              id="kg-target"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="touch-44 w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-white/10 text-white font-mono focus:outline-none focus:border-cyan-500"
            >
              {INDICATORS.map((ind) => (
                <option key={ind.id} value={ind.id}>{ind.id} ({ind.label})</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Path visual: the actual traversed chain, in order */}
      <div aria-hidden="true" className="reveal-gsap rounded-2xl border border-white/[0.08] bg-gradient-to-r from-brand-600/[0.07] via-cyan-500/[0.05] to-transparent p-4 overflow-hidden">
        <div className="flex items-center gap-2 overflow-x-auto">
          {(pathData && pathData.relationships.length > 0
            ? [pathData.relationships[0].source_indicator_id, ...pathData.relationships.map((r) => r.target_indicator_id)]
            : [source, target]
          ).map((node, i) => (
            <React.Fragment key={`${node}-${i}`}>
              {i > 0 && (
                <span className="flex items-center gap-2 shrink-0 px-1">
                  <span className="hidden sm:block h-px w-10 sm:w-16 bg-gradient-to-r from-brand-400/60 to-cyan-400/60" />
                  <ArrowRight className="w-4 h-4 text-cyan-300" />
                </span>
              )}
              <span className="shrink-0 px-3.5 py-2 rounded-xl bg-slate-900/80 border border-cyan-500/25 text-[11px] font-mono text-cyan-200 whitespace-nowrap">
                {shortName(node)}
              </span>
            </React.Fragment>
          ))}
          <span className="ml-auto shrink-0 text-[11px] font-mono text-slate-500 hidden md:block">
            {pathData ? `${pathData.hops} hops • ${pathData.total_lag_months}M lag` : loading ? 'Traversing…' : 'Shortest-path traversal'}
          </span>
        </div>
      </div>

      {error && (
        <div role="alert" className="p-4 rounded-2xl glass-panel border border-rose-500/30 text-xs text-rose-300 font-mono">
          {error}
        </div>
      )}

      {loading && !pathData && !impactData && (
        <div className="p-6 rounded-2xl glass-panel space-y-3" role="status" aria-label="Loading causal transmission">
          <div className="skeleton h-5 rounded w-1/3" />
          <div className="skeleton h-3 rounded w-full" />
          <div className="skeleton h-3 rounded w-11/12" />
        </div>
      )}

      {/* Path Results */}
      {pathData && (
        <div aria-live="polite" className="reveal-gsap cv-auto p-4 sm:p-6 rounded-2xl glass-panel border border-cyan-500/20 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white text-sm">Discovered Transmission Route</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                {pathData.hops} Hops • {pathData.total_lag_months} Months Total Lag
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-500">Shortest Path Traversal</span>
          </div>

          <div className="space-y-3">
            {pathData.relationships.length > 0 ? (
              pathData.relationships.map((rel) => (
                <div
                  key={rel.relation_id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-2 text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 font-mono">
                      <span className="text-brand-300 font-medium truncate max-w-xs">{shortName(rel.source_indicator_id)}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="text-emerald-300 font-medium truncate max-w-xs">{shortName(rel.target_indicator_id)}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-white/5 text-slate-300">{rel.relation_type}</span>
                      <span className="text-cyan-400">Lag: {rel.transmission_lag_months}M</span>
                      <span className="text-slate-300">Sign: {rel.elasticity_sign}</span>
                      <span className="text-slate-300">Conf: {rel.confidence_score.toFixed(2)}</span>
                    </div>
                  </div>
                  <p className="text-slate-400 leading-relaxed">{rel.mechanism_description}</p>
                  <p className="text-[10px] font-mono text-slate-600">{rel.relation_id}</p>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 py-4 text-center">
                {source === target
                  ? 'Source and target are the same indicator.'
                  : 'No causal transmission path exists between these indicators in the ontology.'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Downstream Reachable Targets */}
      {impactData && (
        <div className="p-6 rounded-2xl glass-panel border border-white/5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Share2 className="w-4 h-4 text-brand-400" />
              <span>Downstream Reachable Indicators ({impactData.reachable_targets_count})</span>
            </h3>
            <span className="text-xs font-mono text-slate-400">Knowledge Graph Depth</span>
          </div>

          {impactData.downstream_impacts.length === 0 ? (
            <div className="text-xs text-slate-400 py-2">This indicator has no downstream transmission channels.</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {impactData.downstream_impacts.slice(0, 9).map((imp) => (
                <TiltCard key={imp.target_indicator_id} label="Reachable indicator" maxTilt={5}>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-white/5 text-xs font-mono h-full">
                    <div className="text-white truncate font-medium">{imp.target_name}</div>
                    <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
                      <span>{imp.path_length_hops} hop{imp.path_length_hops === 1 ? '' : 's'} • {imp.total_lag_months}M lag</span>
                      <span className="text-emerald-400">Conf {imp.cumulative_confidence.toFixed(2)}</span>
                    </div>
                  </div>
                </TiltCard>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
