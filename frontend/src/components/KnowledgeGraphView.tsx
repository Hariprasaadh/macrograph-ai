import React, { useState, useEffect } from 'react';
import { Share2, ArrowRight, Zap, RefreshCw } from 'lucide-react';

export const KnowledgeGraphView: React.FC = () => {
  const [source, setSource] = useState('in.macro.monetary.repo_rate');
  const [target, setTarget] = useState('in.macro.monetary.bank_credit_growth');
  const [pathData, setPathData] = useState<any>(null);
  const [impactData, setImpactData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchCausalData = async () => {
    setLoading(true);
    try {
      const [pRes, iRes] = await Promise.all([
        fetch(`/api/v1/kg/path?source_id=${encodeURIComponent(source)}&target_id=${encodeURIComponent(target)}`),
        fetch(`/api/v1/kg/impacts?shock_id=${encodeURIComponent(source)}`),
      ]);
      if (pRes.ok) {
        const pJson = await pRes.json();
        setPathData(pJson);
      }
      if (iRes.ok) {
        const iJson = await iRes.json();
        setImpactData(iJson);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCausalData();
  }, [source, target]);

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-background">
      <div className="pb-6 border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
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
          onClick={fetchCausalData}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl glass-panel hover:bg-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-all self-start md:self-auto"
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
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Source Shock Indicator</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-white/10 text-white font-mono focus:outline-none focus:border-cyan-500"
            >
              <option value="in.macro.monetary.repo_rate">in.macro.monetary.repo_rate (Policy Repo Rate)</option>
              <option value="in.macro.prices.brent_crude">in.macro.prices.brent_crude (Brent Crude Shock)</option>
              <option value="in.macro.prices.cpi_headline">in.macro.prices.cpi_headline (Headline CPI)</option>
              <option value="in.macro.external.usd_inr">in.macro.external.usd_inr (USD/INR Exchange)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Target Response Indicator</label>
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-white/10 text-white font-mono focus:outline-none focus:border-cyan-500"
            >
              <option value="in.macro.monetary.bank_credit_growth">in.macro.monetary.bank_credit_growth (Bank Credit)</option>
              <option value="in.macro.real.gdp_growth">in.macro.real.gdp_growth (Real GDP Growth)</option>
              <option value="in.macro.capmarkets.nifty_50">in.macro.capmarkets.nifty_50 (NIFTY 50 Equity)</option>
              <option value="in.macro.prices.cpi_headline">in.macro.prices.cpi_headline (CPI Inflation)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Path Results */}
      {pathData && (
        <div className="p-6 rounded-2xl glass-panel border border-cyan-500/20 space-y-4">
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
            {pathData.relationships?.length > 0 ? (
              pathData.relationships.map((rel: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-2.5 font-mono">
                    <span className="text-brand-300 font-medium truncate max-w-xs">{rel.source_id}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="text-emerald-300 font-medium truncate max-w-xs">{rel.target_id}</span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                    <span className="px-2 py-0.5 rounded bg-white/5 text-slate-300">
                      Tier: {rel.relationship_type}
                    </span>
                    <span className="text-cyan-400">Lag: {rel.transmission_lag_months}M</span>
                    <span className="text-slate-300">Elasticity: {rel.elasticity_coefficient ?? '-'}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 py-4 text-center">
                Direct single-step transmission verified between indicators.
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

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {impactData.downstream_impacts?.slice(0, 9).map((imp: any, i: number) => (
              <div key={i} className="p-3 rounded-xl bg-slate-900/40 border border-white/5 text-xs font-mono">
                <div className="text-white truncate font-medium">{imp.target_id || imp}</div>
                <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
                  <span>Reachable via transmission</span>
                  <span className="text-emerald-400">Causal Link</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
