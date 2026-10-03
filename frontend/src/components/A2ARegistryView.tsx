import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, ShieldCheck, Search, Inbox } from 'lucide-react';

export const A2ARegistryView: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return agents;
    return agents.filter((card) =>
      [card.name, card.description, card.domain, card.sector].filter(Boolean).join(' ').toLowerCase().includes(q)
    );
  }, [agents, query]);

  const fetchRegistry = async () => {
    setLoading(true);
    try {
      const res = await fetch('/a2a/registry');
      if (res.ok) {
        const json = await res.json();
        setAgents(json.agents || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistry();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-background">
      <div className="pb-6 border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              A2A Standard Protocol
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400 font-mono">Agent Card Discovery Registry</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Registered A2A Domain Agent Cards
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Explore discoverable skills, communication capabilities, and cryptographic schemas for all active agents.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 self-start md:self-auto w-full md:w-auto">
          <div className="relative">
            <label htmlFor="a2a-search" className="sr-only">Search agent cards</label>
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              id="a2a-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search agents, domains…"
              className="touch-44 w-full sm:w-56 pl-9 pr-3 py-2 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400/60"
            />
          </div>
          <button
            onClick={fetchRegistry}
            disabled={loading}
            aria-label="Refresh registry"
            className="touch-44 flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl glass-panel hover:bg-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-all disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Registry</span>
          </button>
        </div>
      </div>

      {loading && agents.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" role="status" aria-label="Loading agent registry">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="p-6 rounded-2xl glass-panel space-y-3">
              <div className="skeleton h-4 rounded w-1/4" />
              <div className="skeleton h-5 rounded w-2/3" />
              <div className="skeleton h-3 rounded w-full" />
              <div className="skeleton h-3 rounded w-5/6" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-10 rounded-2xl glass-panel border border-white/5 text-center space-y-3">
          <Inbox className="w-8 h-8 text-slate-500 mx-auto" />
          <p className="text-sm text-slate-300 font-medium">No agent cards match “{query}”.</p>
          <p className="text-xs text-slate-500">Try a different keyword, or refresh the registry.</p>
        </div>
      ) : (
      <div aria-live="polite" className="cv-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {filtered.map((card, idx) => (
          <div key={idx} className="p-6 rounded-2xl glass-panel border border-white/5 space-y-4 relative group">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v{card.version || '1.0.0'}
                </span>
                <h3 className="text-base font-bold text-white mt-2">{card.name}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{card.description}</p>
              </div>
            </div>

            <div className="pt-3 border-t border-white/5 space-y-2 text-xs">
              <div className="text-[11px] font-mono text-slate-400">
                <span className="text-slate-500">Domain: </span>
                <span className="text-slate-200">{card.domain || card.sector}</span>
              </div>
              <div className="text-[11px] font-mono text-slate-400">
                <span className="text-slate-500">Skills ({card.skills?.length || 0}): </span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {card.skills?.slice(0, 3).map((sk: any, i: number) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-md bg-slate-900 border border-white/5 text-[10px] text-cyan-300 font-mono"
                    >
                      {sk.name || sk}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono">
              <span className="flex items-center gap-1 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                A2A Verified
              </span>
              <span>FastMCP Tool Ready</span>
            </div>
          </div>
        ))}
      </div>
      )}
    </div>
  );
};
