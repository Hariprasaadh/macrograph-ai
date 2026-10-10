import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Flag, RefreshCw } from 'lucide-react';
import type { BriefEnvelope } from '../../types/research';

interface EarlyWarningBriefProps {
  /** Rendered unchanged whenever the new brief is unavailable, so the dashboard never regresses. */
  fallback: React.ReactNode;
}

export const EarlyWarningBrief: React.FC<EarlyWarningBriefProps> = ({ fallback }) => {
  const [env, setEnv] = useState<BriefEnvelope | null>(null);
  const [failed, setFailed] = useState(false);
  const [running, setRunning] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/v1/brief/today', { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((j: BriefEnvelope) => setEnv(j))
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === 'AbortError')) setFailed(true); });
    return () => controller.abort();
  }, []);

  const refresh = useCallback(async () => {
    if (running) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setToast(null);
    try {
      const res = await fetch('/api/v1/brief/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', signal: controller.signal });
      if (res.status === 409) { setToast('A run is already in progress.'); return; }
      if (!res.ok) throw new Error(String(res.status));
      const json = (await res.json()) as BriefEnvelope;
      setEnv(json);
      setFailed(false);
      if (json.served_from_cache) setToast('Served from cache (last run < 15 min ago).');
    } catch (e) {
      if (!(e instanceof DOMException && e.name === 'AbortError')) setToast('Brief run failed; showing the previous brief.');
    } finally {
      setRunning(false);
    }
  }, [running]);

  const brief = env?.brief ?? null;
  if (failed && !brief) return <>{fallback}</>;

  const severityStyle = (s: string) =>
    s === 'CRITICAL' ? 'border-rose-500/40 bg-rose-500/5' : s === 'WATCH' ? 'border-amber-500/40 bg-amber-500/5' : 'border-cyan-500/30 bg-cyan-500/5';

  return (
    <div className="space-y-4">
      <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-white/10 space-y-4 shadow-2xl">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20"><Flag className="w-4 h-4" /></span>
            <span className="text-[11px] font-mono uppercase tracking-wider text-amber-300 font-bold">Early-Warning Brief</span>
            {env && (env.is_stale
              ? <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">STALE · not generated today</span>
              : <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">FRESH · AUTO 08:15 IST</span>)}
          </div>
          <button onClick={() => void refresh()} disabled={running}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-white/10 text-xs font-mono text-slate-200 flex items-center gap-2 disabled:opacity-60">
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${running ? 'animate-spin' : ''}`} />{running ? 'Running…' : brief ? 'Refresh' : 'Generate brief'}
          </button>
        </div>
        {toast && <div className="text-[11px] font-mono text-amber-300">{toast}</div>}

        {brief ? (
          <>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white leading-snug">{brief.headline}</h2>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">{brief.executive_summary}</p>
              <div className="text-[10px] font-mono text-slate-500 mt-1">{brief.date} · generated {brief.created_at}</div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-amber-400" />Early warnings</div>
              {brief.warnings.length === 0 && <div className="text-xs text-slate-500 font-mono">No statistical anomalies flagged in the available series.</div>}
              {brief.warnings.map((w) => (
                <div key={w.title} className={`p-3 rounded-xl border ${severityStyle(w.severity)} space-y-1.5`}>
                  <div className="flex items-center justify-between text-xs"><span className="text-slate-100 font-semibold">{w.title}</span><span className="font-mono text-[10px] text-slate-300">{w.severity}</span></div>
                  <div className="flex flex-wrap gap-1.5">{w.causal_path.map((p, i) => <span key={`${p}-${i}`} className="px-2 py-0.5 rounded bg-white/5 text-[10px] font-mono text-cyan-200">{p}</span>)}</div>
                  <div className="text-[11px] text-slate-400">{w.action}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {brief.key_drivers.map((d) => (
                <div key={d.pillar} className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono"><span className="text-slate-300 font-semibold">{d.pillar}</span><span className="text-[10px] text-slate-300">{d.stance}</span></div>
                  <p className="text-[11px] text-slate-400">{d.takeaway}</p>
                </div>
              ))}
            </div>
            <div className="text-[10px] font-mono text-slate-500 border-t border-white/5 pt-2">
              mode {brief.provenance.mode ?? 'n/a'} · model {brief.llm_model || 'none (deterministic)'} · news {brief.provenance.news_status ?? 'n/a'}
              {brief.provenance.counts ? ` · [${brief.provenance.counts.available} available][${brief.provenance.counts.unavailable} unavailable]` : ''}
            </div>
          </>
        ) : (
          <p className="text-xs text-slate-400 font-mono">No brief has been generated yet. Press “Generate brief”; the dashboard card below stays available.</p>
        )}
      </div>
      {!brief && fallback}
    </div>
  );
};
