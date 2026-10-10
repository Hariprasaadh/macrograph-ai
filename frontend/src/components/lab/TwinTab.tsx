import React, { useEffect, useMemo, useState } from 'react';
import type { CompareResponse } from '../../types/research';
import { AnimatedKgSvg, type EdgeStyle } from './AnimatedKgSvg';
import { MiniLines } from './MiniLines';
import { postJson, useKgGraph } from './useResearchApi';

const PRESETS = [
  { id: 'in.macro.prices.brent_crude', label: 'Brent crude (USD/bbl)', min: -20, max: 50, step: 5, def: 20 },
  { id: 'in.macro.monetary.repo_rate', label: 'Repo rate (pp)', min: -1, max: 2, step: 0.25, def: 0.5 },
  { id: 'in.macro.external.usd_inr', label: 'USD/INR (INR)', min: -3, max: 10, step: 0.5, def: 3.5 },
];

export const TwinTab: React.FC = () => {
  const { graph, error: graphError } = useKgGraph();
  const [shockId, setShockId] = useState(PRESETS[0].id);
  const [magnitude, setMagnitude] = useState(PRESETS[0].def);
  const [data, setData] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  const preset = PRESETS.find((p) => p.id === shockId) ?? PRESETS[0];

  // The engine is linear, so the server is called once per shock variable; the slider is then network-free.
  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    postJson<CompareResponse>('/api/v1/research/compare', { shock_variable: shockId, shock_magnitude: preset.def }, controller.signal)
      .then((res) => {
        setData(res);
        setTarget(Object.keys(res.attribution)[Object.keys(res.attribution).length - 1] ?? null);
      })
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(e instanceof Error ? e.message : 'Request failed'); });
    return () => controller.abort();
  }, [shockId, preset.def]);

  const rows = useMemo(() => {
    if (!data) return [];
    return Object.keys(data.attribution).map((id) => {
      const delta = data.gain_per_unit[id] * magnitude;
      const base = data.base[id];
      return { id, name: data.names[id] ?? id, base, shocked: base + delta, delta, pct: base ? (delta / Math.abs(base)) * 100 : 0, lag: data.lag_months[id] ?? 0 };
    });
  }, [data, magnitude]);
  const maxPct = Math.max(1e-9, ...rows.map((r) => Math.abs(r.pct)));
  const attr = target && data ? data.attribution[target] : null;
  const targetRow = rows.find((r) => r.id === target);

  const edgeStyle = useMemo(() => {
    const out: Record<string, EdgeStyle> = {};
    graph?.edges.forEach((e) => { out[e.relation_id] = { dim: true }; });
    attr?.edges.forEach((e, i) => {
      out[e.relation_id] = { color: e.sign === '-' ? '#fb7185' : '#34d399', width: 2 + attr.share[i] * 14 };
    });
    return out;
  }, [attr, graph]);
  const involved = useMemo(() => new Set(attr ? [data!.shock_variable, ...attr.edges.map((e) => e.to)] : []), [attr, data]);

  const lines = targetRow && data ? [
    { label: 'baseline world', color: '#60a5fa', points: Array.from({ length: 13 }, (_, t) => ({ t, value: targetRow.base })) },
    { label: 'shocked world', color: '#f59e0b', dashed: true, points: Array.from({ length: 13 }, (_, t) => ({ t, value: t < targetRow.lag ? targetRow.base : targetRow.shocked })) },
  ] : [];

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-2xl glass-panel border border-white/10 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <label className="space-y-1.5">
          <span className="text-slate-400">Shock variable</span>
          <select value={shockId} onChange={(e) => { const p = PRESETS.find((x) => x.id === e.target.value)!; setShockId(p.id); setMagnitude(p.def); }}
            className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-white">
            {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </label>
        <label className="space-y-1.5 md:col-span-2">
          <span className="text-slate-400">Magnitude <span className="text-amber-300 font-bold">{magnitude > 0 ? '+' : ''}{magnitude}</span> <span className="text-slate-500">(slider is computed in the browser, no request)</span></span>
          <input type="range" min={preset.min} max={preset.max} step={preset.step} value={magnitude} onChange={(e) => setMagnitude(Number(e.target.value))} className="w-full accent-amber-400" />
        </label>
      </div>
      {(error || graphError) && <div role="alert" className="p-3 rounded-xl glass-panel border border-rose-500/30 text-xs text-rose-300 font-mono">{error ?? graphError}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="p-4 rounded-2xl glass-panel border border-white/10 space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">Change vs baseline (% of baseline, click a row)</h4>
          {rows.map((r) => (
            <button key={r.id} onClick={() => setTarget(r.id)} className={`w-full text-left p-2 rounded-xl border ${target === r.id ? 'border-cyan-500/40 bg-cyan-500/5' : 'border-white/5 bg-slate-900/40'}`}>
              <div className="flex justify-between text-[11px] font-mono text-slate-300"><span className="truncate">{r.name}</span><span className={r.delta >= 0 ? 'text-amber-300' : 'text-cyan-300'}>{r.delta >= 0 ? '+' : ''}{r.delta.toFixed(3)} ({r.pct.toFixed(2)}%)</span></div>
              <div className="h-1.5 mt-1 rounded bg-slate-800 overflow-hidden"><div className="h-full" style={{ width: `${(Math.abs(r.pct) / maxPct) * 100}%`, backgroundColor: r.delta >= 0 ? '#f59e0b' : '#22d3ee' }} /></div>
            </button>
          ))}
        </div>
        <div className="p-4 rounded-2xl glass-panel border border-white/10 space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">{targetRow ? targetRow.name : 'Select an indicator'} · baseline vs shocked</h4>
          {lines.length > 0 && <MiniLines series={lines} />}
          {targetRow && <p className="text-[11px] font-mono text-slate-400">baseline {targetRow.base} → shocked {targetRow.shocked.toFixed(3)} after {targetRow.lag}M. The baseline is flat by construction (the engine has no baseline dynamics); the content is the delta and its path.</p>}
          {attr && (
            <div className="text-[11px] font-mono space-y-1 pt-2 border-t border-white/5">
              <div className="text-slate-300">Attenuation share per hop · sign flips: {attr.sign_flips}</div>
              {attr.edges.map((e, i) => (
                <div key={e.relation_id} className={`flex justify-between ${e.relation_id === attr.weakest_link ? 'text-amber-300' : 'text-slate-400'}`}>
                  <span>{e.from.split('.').pop()} → {e.to.split('.').pop()} ({e.sign}, conf {e.confidence}){e.note ? ' ⚠' : ''}</span>
                  <span>{(attr.share[i] * 100).toFixed(1)}%{e.relation_id === attr.weakest_link ? ' ← weakest link' : ''}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-3 rounded-2xl glass-panel border border-white/10">
        {graph ? <AnimatedKgSvg graph={graph} involved={attr ? involved : undefined} edgeStyle={edgeStyle} /> : <div className="skeleton h-64 rounded-xl" />}
        <p className="text-[10px] font-mono text-slate-500 mt-1">edge colour: green = positive, red = negative · thickness = share of total attenuation on the selected path · SIM, heuristic graph-attenuation model</p>
      </div>
    </div>
  );
};
