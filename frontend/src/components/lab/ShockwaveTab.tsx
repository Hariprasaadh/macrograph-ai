import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, AlertTriangle } from 'lucide-react';
import { gsap, prefersReducedMotion } from '../../motion/gsapSetup';
import type { TrajectoryResponse } from '../../types/research';
import { AnimatedKgSvg, type EdgeStyle } from './AnimatedKgSvg';
import { MiniLines } from './MiniLines';
import { postJson, useKgGraph } from './useResearchApi';

const PRESETS = [
  { id: 'in.macro.prices.brent_crude', label: 'Brent crude (USD/bbl)', min: -20, max: 50, step: 5, def: 20 },
  { id: 'in.macro.monetary.repo_rate', label: 'Repo rate (pp)', min: -1, max: 2, step: 0.25, def: 0.5 },
  { id: 'in.macro.external.usd_inr', label: 'USD/INR (INR)', min: -3, max: 10, step: 0.5, def: 3.5 },
  { id: 'in.macro.agri.monsoon_departure', label: 'Monsoon departure (%)', min: -30, max: 20, step: 5, def: -10 },
  { id: 'in.macro.fiscal.central_capex', label: 'Central capex (INR Cr)', min: -20000, max: 50000, step: 5000, def: 20000 },
];
const COLORS = ['#22d3ee', '#f59e0b', '#34d399', '#f472b6', '#818cf8'];

export const ShockwaveTab: React.FC = () => {
  const { graph, error: graphError } = useKgGraph();
  const [shockId, setShockId] = useState(PRESETS[0].id);
  const [magnitude, setMagnitude] = useState(PRESETS[0].def);
  const [shape, setShape] = useState<'step' | 'decay'>('step');
  const [data, setData] = useState<TrajectoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const tween = useRef<ReturnType<typeof gsap.to> | null>(null);
  const proxy = useRef({ t: 0 });
  const preset = PRESETS.find((p) => p.id === shockId) ?? PRESETS[0];

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    postJson<TrajectoryResponse>('/api/v1/research/trajectory',
      { shock_variable: shockId, shock_magnitude: magnitude, horizon_months: 12, shape, half_life_months: shape === 'decay' ? 4 : null },
      controller.signal)
      .then((res) => { setData(res); setSelected(null); })
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === 'AbortError')) setError(e instanceof Error ? e.message : 'Request failed'); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [shockId, magnitude, shape]);

  useEffect(() => () => { tween.current?.kill(); }, []);

  const horizon = data?.horizon_months ?? 12;
  const play = () => {
    tween.current?.kill();
    proxy.current.t = 0;
    setT(0);
    if (prefersReducedMotion()) { proxy.current.t = horizon; setT(horizon); return; }
    setPlaying(true);
    tween.current = gsap.to(proxy.current, {
      t: horizon, duration: 8, ease: 'none',
      onUpdate: () => setT(proxy.current.t),
      onComplete: () => setPlaying(false),
    });
  };
  const pause = () => { tween.current?.kill(); setPlaying(false); };

  const arrival = useMemo(() => Object.fromEntries((data?.nodes ?? []).map((n) => [n.id, n.lag_months])), [data]);
  const involved = useMemo(() => new Set((data?.nodes ?? []).map((n) => n.id)), [data]);
  const intensity = useMemo(() => Object.fromEntries((data?.nodes ?? []).map((n) => [n.id, Math.min(1, Math.abs(n.cum_multiplier) * 1.6 + 0.15)])), [data]);
  const edgeStyle = useMemo(() => {
    const out: Record<string, EdgeStyle> = {};
    (data?.edges ?? []).forEach((e) => { out[e.relation_id] = { width: 1.5 + e.confidence * 3 }; });
    graph?.edges.forEach((e) => { if (!out[e.relation_id]) out[e.relation_id] = { dim: true }; });
    return out;
  }, [data, graph]);

  const chartNodes = useMemo(() => {
    const nodes = data?.nodes ?? [];
    const picked = selected ? nodes.filter((n) => n.id === selected) : [];
    const rest = nodes.filter((n) => n.id !== data?.shock.id && n.id !== selected).slice(0, selected ? 3 : 4);
    return [...picked, ...rest];
  }, [data, selected]);

  const reached = (data?.edges ?? []).filter((e) => (arrival[e.from] ?? 0) <= t && (arrival[e.to] ?? 0) <= t && (arrival[e.to] ?? 0) > 0);
  const selNode = data?.nodes.find((n) => n.id === selected) ?? null;

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-2xl glass-panel border border-white/10 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
        <label className="space-y-1.5">
          <span className="text-slate-400">Shock variable</span>
          <select value={shockId} onChange={(e) => { const p = PRESETS.find((x) => x.id === e.target.value)!; setShockId(p.id); setMagnitude(p.def); setT(0); }}
            className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-white">
            {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </label>
        <label className="space-y-1.5">
          <span className="text-slate-400">Magnitude <span className="text-amber-300 font-bold">{magnitude > 0 ? '+' : ''}{magnitude}</span></span>
          <input type="range" min={preset.min} max={preset.max} step={preset.step} value={magnitude}
            onChange={(e) => setMagnitude(Number(e.target.value))} className="w-full accent-amber-400" />
        </label>
        <div className="space-y-1.5">
          <span className="text-slate-400">Response shape</span>
          <div className="flex gap-2">
            {(['step', 'decay'] as const).map((s) => (
              <button key={s} onClick={() => setShape(s)}
                className={`flex-1 py-2 rounded-xl border ${shape === s ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-200' : 'bg-slate-950/60 border-white/10 text-slate-400'}`}>
                {s === 'step' ? 'step' : 'decay (illustrative)'}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-end gap-2">
          <button onClick={playing ? pause : play} disabled={!data || loading}
            className="flex-1 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 font-semibold flex items-center justify-center gap-2 disabled:opacity-50">
            {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}{playing ? 'Pause' : 'Play'}
          </button>
          <span className="px-2 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px]">SIM</span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
        <span>month</span>
        <input type="range" min={0} max={horizon} step={0.1} value={t}
          onChange={(e) => { tween.current?.kill(); setPlaying(false); proxy.current.t = Number(e.target.value); setT(Number(e.target.value)); }}
          className="flex-1 accent-cyan-400" />
        <span className="text-cyan-300 font-bold w-16 text-right">t = {t.toFixed(1)} / {horizon}</span>
      </div>

      {(error || graphError) && <div role="alert" className="p-3 rounded-xl glass-panel border border-rose-500/30 text-xs text-rose-300 font-mono">{error ?? graphError}</div>}

      <div className="p-3 rounded-2xl glass-panel border border-white/10">
        {graph ? (
          <AnimatedKgSvg graph={graph} arrival={arrival} activeTime={data ? t : null} intensity={intensity}
            involved={data ? involved : undefined} edgeStyle={edgeStyle} selectedId={selected} onSelectNode={setSelected} />
        ) : <div className="skeleton h-64 rounded-xl" />}
        <p className="text-[10px] font-mono text-slate-500 mt-1">
          glowing = reached by t · glow strength = unit-free |cumulative multiplier| · edge width = confidence · ⚠ = edge under review · click a node
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="p-4 rounded-2xl glass-panel border border-white/10 space-y-2">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">Impulse responses (each line on its own scale)</h4>
          <MiniLines cursor={t} series={chartNodes.map((n, i) => ({ label: n.name, color: COLORS[i % COLORS.length], points: n.series }))} />
          {selNode && (
            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-white/5">
              {selNode.name}: arrives month {selNode.lag_months}, Δ peak {selNode.delta_peak} ({selNode.delta_pct_of_baseline ?? 'n/a'}% of baseline), {selNode.hops} hop(s)
            </div>
          )}
        </div>
        <div className="p-4 rounded-2xl glass-panel border border-white/10 space-y-2 max-h-80 overflow-y-auto">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">Hop provenance (edges fired by t)</h4>
          {reached.length === 0 && <p className="text-xs text-slate-500">Press Play or scrub the month slider.</p>}
          {reached.map((e) => (
            <div key={e.relation_id} className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 text-[11px] font-mono space-y-1">
              <div className="text-slate-200">{e.from.split('.').pop()} → {e.to.split('.').pop()} <span className="text-cyan-300">lag {e.lag_months}M · conf {e.confidence.toFixed(2)} · {e.sign}</span></div>
              <div className="text-slate-500">{e.relation_id} · {e.type} · {e.evidence_class ?? 'SEEDED'}{e.seeded_p != null ? ` p=${e.seeded_p}` : ''}</div>
              {e.mechanism && <div className="text-slate-400 font-sans">{e.mechanism}</div>}
              {e.note && <div className="text-amber-300 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{e.note}</div>}
            </div>
          ))}
        </div>
      </div>
      {data && <ul className="text-[10px] font-mono text-slate-500 list-disc pl-5">{data.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
    </div>
  );
};
