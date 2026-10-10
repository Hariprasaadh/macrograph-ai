import React, { useEffect, useMemo, useState } from 'react';
import type { AnomalyItem, AnomalyResponse } from '../../types/research';
import { AnimatedKgSvg, type EdgeStyle } from './AnimatedKgSvg';
import { getJson, useKgGraph } from './useResearchApi';

const CLASS_STYLE: Record<AnomalyItem['class'], string> = {
  PROPAGATING: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  ISOLATED: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  UNLINKED: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
};
const INJECTABLE = [
  { id: 'in.macro.external.trade_balance', label: 'Trade balance' },
  { id: 'in.macro.external.usd_inr', label: 'USD/INR' },
  { id: 'in.macro.monetary.bank_credit_growth', label: 'Bank credit growth' },
  { id: 'in.macro.capmarkets.india_vix', label: 'India VIX' },
];

export const RadarTab: React.FC = () => {
  const { graph } = useKgGraph();
  const [data, setData] = useState<AnomalyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sim, setSim] = useState(false);
  const [injectId, setInjectId] = useState(INJECTABLE[0].id);
  const [injectZ, setInjectZ] = useState(-3);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const url = sim ? `/api/v1/research/anomalies?inject=${encodeURIComponent(`${injectId}:${injectZ}`)}` : '/api/v1/research/anomalies';
    getJson<AnomalyResponse>(url, controller.signal)
      .then((res) => { setData(res); setSelected(res.items[0]?.indicator_id ?? null); })
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(e instanceof Error ? e.message : 'Request failed'); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [sim, injectId, injectZ]);

  const item = data?.items.find((i) => i.indicator_id === selected) ?? null;
  const pulse = useMemo(() => new Set((data?.items ?? []).filter((i) => i.in_graph).map((i) => i.indicator_id)), [data]);
  const involved = useMemo(() => {
    if (!item) return undefined;
    return new Set([item.indicator_id, ...item.neighbors.map((n) => n.id), ...item.expected_propagation.map((e) => e.id)]);
  }, [item]);
  const edgeStyle = useMemo(() => {
    const out: Record<string, EdgeStyle> = {};
    graph?.edges.forEach((e) => { out[e.relation_id] = { dim: !item || !involved?.has(e.from) || !involved?.has(e.to) }; });
    item?.culprit_path.forEach((id) => { out[id] = { color: '#fb7185', width: 4 }; });
    return out;
  }, [graph, item, involved]);

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-2xl glass-panel border border-white/10 flex flex-wrap items-center gap-4 text-xs font-mono">
        <span className="text-slate-300">z-score vs trailing {data?.window ?? 12} points (latest excluded), flag |z| &gt; {data?.threshold ?? 2}</span>
        <label className="flex items-center gap-2 text-slate-300"><input type="checkbox" checked={sim} onChange={(e) => setSim(e.target.checked)} /> SIM replay</label>
        {sim && (
          <>
            <select value={injectId} onChange={(e) => setInjectId(e.target.value)} className="px-2 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-white">
              {INJECTABLE.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
            <label className="flex items-center gap-2 text-slate-400">z <input type="number" step={0.5} value={injectZ} onChange={(e) => setInjectZ(Number(e.target.value))} className="w-20 px-2 py-1 rounded bg-slate-900 border border-white/10 text-white" /></label>
            <span className="px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300">in-memory copy, nothing is written</span>
          </>
        )}
        {loading && <span className="text-slate-500">scanning…</span>}
      </div>
      {error && <div role="alert" className="p-3 rounded-xl glass-panel border border-rose-500/30 text-xs text-rose-300 font-mono">{error}</div>}
      {data?.note && <div className="p-3 rounded-xl glass-panel border border-amber-500/30 text-xs text-amber-300 font-mono">{data.note}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="space-y-3">
          {data && data.items.length === 0 && (
            <div className="p-5 rounded-2xl glass-panel border border-white/10 text-xs font-mono text-slate-400">
              No series exceeded |z| &gt; {data.threshold}. Scanned {data.scanned} series; {data.skipped.length} skipped (need ≥ {data.min_points} points). Try SIM replay to see how the graph would diagnose a shock.
            </div>
          )}
          {data?.items.map((i) => (
            <button key={i.indicator_id} onClick={() => setSelected(i.indicator_id)}
              className={`w-full text-left p-3 rounded-xl border bg-slate-900/60 ${selected === i.indicator_id ? 'border-cyan-500/50' : 'border-white/10'}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-white font-semibold">{i.name}</span>
                <span className={`px-2 py-0.5 rounded border text-[10px] font-mono ${CLASS_STYLE[i.class]}`}>{i.class}</span>
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-1">z {i.z >= 0 ? '+' : ''}{i.z} · period {i.period} · {i.labels.data}{i.propagation_score !== null ? ` · propagation ${i.propagation_score}` : ''}</div>
              {i.trust !== 'ok' && <div className="text-[10px] font-mono text-amber-300 mt-1">LOW TRUST — verify source table</div>}
            </button>
          ))}
          {data && data.skipped.length > 0 && (
            <details className="text-[11px] font-mono text-slate-500">
              <summary className="cursor-pointer">{data.skipped.length} series skipped</summary>
              <ul className="list-disc pl-5">{data.skipped.map((s) => <li key={s.indicator_id}>{s.indicator_id} — {s.reason} (n={s.n})</li>)}</ul>
            </details>
          )}
        </div>

        <div className="p-3 rounded-2xl glass-panel border border-white/10 space-y-3">
          {graph ? <AnimatedKgSvg graph={graph} involved={involved} pulse={pulse} edgeStyle={edgeStyle} selectedId={selected} onSelectNode={setSelected} /> : <div className="skeleton h-64 rounded-xl" />}
          {item && (
            <div className="text-[11px] font-mono space-y-1 border-t border-white/5 pt-2">
              <div className="text-slate-300">{item.name}: {item.class}{item.class === 'UNLINKED' ? ' — the graph has no neighbour with data, so it cannot diagnose this deviation.' : ''}</div>
              {item.neighbors.map((n) => <div key={n.id} className="text-slate-400">{n.direction} {n.id.split('.').pop()} z {n.z} (lag {n.lag_months}M)</div>)}
              {item.expected_propagation.length > 0 && (
                <div className="text-slate-500">KG expects movement in: {item.expected_propagation.map((e) => `${e.name} (+${e.lag_months}M)`).join(', ')}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
