import React from 'react';
import { ArrowRight, Network } from 'lucide-react';
import type { A2ASummary } from '../../types';
import type { ConsensusAgent, ConsensusPayload } from '../../types/research';

const statusColor = (a: ConsensusAgent): string => {
  if (a.status === 'failed' || a.status === 'unknown') return 'border-slate-500/40 text-slate-400';
  const cover = a.observations ? a.usable / a.observations : 1;
  if (a.status === 'partial' || cover < 0.7) return cover < 0.7 && a.status !== 'partial' ? 'border-rose-500/40 text-rose-300' : 'border-amber-500/40 text-amber-300';
  return cover >= 0.85 ? 'border-emerald-500/40 text-emerald-300' : 'border-amber-500/40 text-amber-300';
};

export const DebateDag: React.FC<{ consensus: ConsensusPayload; a2a?: A2ASummary }> = ({ consensus, a2a }) => {
  const { agents, kg, scores } = consensus;
  const box = 'px-3 py-2 rounded-xl bg-slate-900/80 border text-[11px] font-mono';
  const quality = scores.consensus_quality;
  return (
    <section aria-label="Multi-agent debate DAG" className="mt-4 p-3 rounded-xl bg-slate-950 border border-white/10">
      <div className="flex items-center gap-2 text-xs font-mono mb-3">
        <Network className="w-3.5 h-3.5 text-indigo-400" />
        <span className="text-indigo-300 font-semibold">Debate DAG</span>
        <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400">consensus quality {quality.toFixed(2)} (heuristic)</span>
      </div>
      <div className="flex flex-col lg:flex-row lg:items-center gap-3 overflow-x-auto">
        <div className={`${box} border-cyan-500/40 text-cyan-200 shrink-0`}>
          Routing<br /><span className="text-slate-400">{consensus.routing_method ?? a2a?.routing_method ?? 'n/a'}</span>
        </div>
        <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden lg:block" />
        <div className="flex flex-col gap-2 shrink-0">
          {agents.length === 0 && <div className={`${box} border-slate-500/40 text-slate-400`}>no agents recorded</div>}
          {agents.map((a) => (
            <div key={a.agent_id} className={`${box} ${statusColor(a)}`}>
              <div className="font-semibold">{a.agent_id}</div>
              <div className="text-slate-400">
                {a.status}{a.duration_ms ? ` · ${(a.duration_ms / 1000).toFixed(1)}s` : ''} · {a.usable}/{a.observations} obs · {a.sources} src
              </div>
              {a.errors.length > 0 && <div className="text-rose-300">{a.errors.join(', ')}</div>}
            </div>
          ))}
          {consensus.peer_calls > 0 && <div className="text-[10px] font-mono text-slate-500">+ {consensus.peer_calls} peer follow-up request(s)</div>}
        </div>
        <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden lg:block" />
        <div className={`${box} border-cyan-500/40 text-cyan-200 shrink-0`}>
          KG enrichment<br /><span className="text-slate-400">{kg.paths} path(s){kg.scenario ? ' · scenario' : ''} · cover {kg.coverage}</span>
        </div>
        <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden lg:block" />
        <div className={`${box} border-indigo-500/40 text-indigo-200 shrink-0`}>
          Synthesis<br /><span className="text-slate-400">confidence {scores.confidence_score ?? 'n/a'}</span>
        </div>
      </div>
      <div className="mt-3 text-[10px] font-mono text-slate-500">
        agents {scores.agent_success} × evidence {scores.evidence_cover} × (0.5 + 0.5 × KG {scores.kg_cover}) · green ≥ 85% usable evidence, amber 70–85%, red &lt; 70%, grey = no data
      </div>
    </section>
  );
};
