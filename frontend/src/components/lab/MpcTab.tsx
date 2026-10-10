import React, { useState } from 'react';
import { Gavel } from 'lucide-react';
import type { MpcResponse } from '../../types/research';
import { postJson } from './useResearchApi';

const VOTE_STYLE: Record<string, string> = {
  HIKE: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  HOLD: 'bg-slate-500/20 text-slate-200 border-slate-500/40',
  CUT: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
};

export const MpcTab: React.FC = () => {
  const [data, setData] = useState<MpcResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useLlm, setUseLlm] = useState(true);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await postJson<MpcResponse>('/api/v1/research/mpc/simulate', { use_llm: useLlm }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-2xl glass-panel border border-amber-500/20 flex flex-wrap items-center gap-4 text-xs font-mono">
        <span className="px-2 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300">SIMULATED — archetype personas, not a forecast of the real RBI MPC</span>
        <label className="flex items-center gap-2 text-slate-300"><input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> use LLM wording when a key exists</label>
        <button onClick={run} disabled={loading} className="ml-auto px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 font-semibold flex items-center gap-2 disabled:opacity-50">
          <Gavel className="w-3.5 h-3.5" />{loading ? 'Deliberating…' : 'Run simulation'}
        </button>
      </div>
      {error && <div role="alert" className="p-3 rounded-xl glass-panel border border-rose-500/30 text-xs text-rose-300 font-mono">{error}</div>}

      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.seats.map((s) => (
              <div key={s.seat} className="p-3 rounded-xl bg-slate-900/60 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-200 font-semibold">{s.seat}</span>
                  <span className={`px-2 py-0.5 rounded border text-[11px] font-mono font-bold ${VOTE_STYLE[s.vote]}`}>{s.vote}</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">{s.reason}</p>
                <div className="text-[10px] font-mono text-slate-500">{s.persona} · {s.source}{s.cited_indicator ? ` · cites ${s.cited_indicator.split('.').pop()}` : ''}</div>
              </div>
            ))}
          </div>
          <div className="p-4 rounded-2xl glass-panel border border-white/10 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <div className="text-slate-400 mb-1">Tally</div>
              <div className="flex gap-2">{Object.entries(data.tally).map(([k, v]) => <span key={k} className={`px-2 py-1 rounded border ${VOTE_STYLE[k]}`}>{k} {v}</span>)}</div>
              <div className="mt-2 text-white text-base font-bold">Decision: {data.decision}</div>
            </div>
            <div>
              <div className="text-slate-400 mb-1">Dissent</div>
              <div className="h-2 rounded bg-slate-800 overflow-hidden"><div className="h-full bg-amber-400" style={{ width: `${data.dissent * 100}%` }} /></div>
              <div className="mt-1 text-slate-300">{Math.round(data.dissent * 100)}%</div>
            </div>
            <div>
              <div className="text-slate-400 mb-1">Rule baseline (no LLM)</div>
              <div className={data.agrees_with_rule_baseline ? 'text-emerald-300' : 'text-amber-300'}>{data.rule_baseline.decision} — {data.agrees_with_rule_baseline ? 'agrees' : 'differs'}</div>
              <div className="text-slate-500 mt-1">LLM used: {data.labels.llm_used ? 'yes' : 'no (deterministic)'}</div>
            </div>
          </div>
          <div className="p-4 rounded-2xl glass-panel border border-white/10 text-[11px] font-mono space-y-1">
            <div className="text-slate-300 mb-1">Evidence pack (period and freshness shown)</div>
            {data.evidence.map((e) => <div key={e.id} className="text-slate-400">{e.id} = {e.value} (period {e.period}, prior {e.prior_value ?? 'n/a'}, {e.freshness})</div>)}
          </div>
        </>
      )}
    </div>
  );
};
