import React, { useState } from 'react';
import { ChevronDown, Database, GitBranch, Cpu, ShieldCheck } from 'lucide-react';
import type { ModelCardPayload } from '../../types/research';

export const ModelCardStrip: React.FC<{ card: ModelCardPayload }> = ({ card }) => {
  const [open, setOpen] = useState(false);
  const { evidence, kg, model, trust, regime } = card;
  const chip = 'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-white/10 text-[11px] font-mono';
  return (
    <section aria-label="Model card" className="mt-4 p-3 rounded-xl bg-slate-950 border border-white/10 space-y-2">
      <div className="flex flex-wrap gap-2">
        <span className={chip}><Database className="w-3.5 h-3.5 text-emerald-400" />LIVE {evidence.live} · SOURCED {evidence.sourced} · UNAVAIL {evidence.unavailable}</span>
        <span className={chip}><GitBranch className="w-3.5 h-3.5 text-cyan-400" />KG {kg.paths} path{kg.paths === 1 ? '' : 's'}{kg.max_hops ? ` · max ${kg.max_hops} hops` : ''}</span>
        <span className={chip}><Cpu className="w-3.5 h-3.5 text-amber-400" />MODEL {model.name}{model.kind === 'SIM' ? ' · SIM' : ''}</span>
        <button onClick={() => setOpen((v) => !v)} className={`${chip} hover:bg-slate-800`} aria-expanded={open}>
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />TRUST {trust.score.toFixed(2)} ({trust.label})
          <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>
      {open && (
        <div className="text-[11px] font-mono text-slate-400 space-y-2 pt-2 border-t border-white/5">
          <div>trust = 0.4 × evidence {trust.parts.evidence_cover} + 0.3 × mean edge confidence {trust.parts.mean_edge_confidence} + 0.3 × agent success {trust.parts.agent_success}</div>
          {model.formula?.text && <div className="text-slate-300">formula → {model.formula.text}</div>}
          {model.baseline && <div>baseline: {model.baseline}</div>}
          {model.constants && <div>constants: ×{model.constants.attenuation}·conf per hop, ×{model.constants.scale}, band ±{(model.constants.band ?? 0) * 100}% (heuristic, not a CI)</div>}
          {regime.map((r) => <div key={r}>regime: {r}</div>)}
          {kg.relations.length > 0 && (
            <div>
              edges used:
              <ul className="list-disc pl-5">{kg.relations.map((r) => <li key={r.relation_id}>{r.relation_id} — {r.evidence_class}{r.seeded_p != null ? ` (seeded p=${r.seeded_p})` : ''}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
