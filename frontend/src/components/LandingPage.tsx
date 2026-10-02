import React, { useRef } from 'react';
import {
  ShieldCheck,
  Network,
  ArrowRight,
  Database,
  Sparkles,
  Layers,
  GitBranch,
} from 'lucide-react';
import { SECTOR_AGENTS } from '../data/agents';

interface LandingPageProps {
  onOpenAuth: () => void;
  isAuthenticated: boolean;
  onEnterWorkspace: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onOpenAuth,
  isAuthenticated,
  onEnterWorkspace,
}) => {
  const heroRef = useRef<HTMLDivElement>(null);

  return (
    <div className="min-h-screen bg-background text-slate-100 relative overflow-hidden bg-grid-pattern">
      {/* Dynamic ambient radial glowing backdrops */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-radial-gradient pointer-events-none" />
      <div className="absolute top-40 right-[-10%] w-[500px] h-[500px] bg-brand-500/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-80 left-[-10%] w-[500px] h-[500px] bg-accent-cyan/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Top Navigation */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-400 p-[1px] shadow-glow-brand">
              <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
                <Network className="w-5 h-5 text-brand-400" />
              </div>
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Macrograph<span className="text-brand-400 font-extrabold">.AI</span>
              </span>
              <span className="ml-2.5 text-[10px] uppercase tracking-widest font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Live RBI Data
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm text-slate-300">
            <a href="#overview" className="hover:text-white transition-colors">Overview</a>
            <a href="#architecture" className="hover:text-white transition-colors">Dual Protocol</a>
            <a href="#sectors" className="hover:text-white transition-colors">10 Sector Agents</a>
            <a href="#citation-policy" className="hover:text-white transition-colors">Citation Standard</a>
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <button
                onClick={onEnterWorkspace}
                className="py-2.5 px-5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-sm shadow-glow-brand transition-all flex items-center gap-2 group"
              >
                <span>Enter Research Hub</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <button
                onClick={onOpenAuth}
                className="py-2.5 px-5 rounded-xl bg-white text-slate-900 hover:bg-slate-100 font-medium text-sm transition-all flex items-center gap-2.5 shadow-lg group"
              >
                {/* Google Icon */}
                <svg viewBox="0 0 24 24" className="w-4 h-4">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section ref={heroRef} className="pt-20 pb-16 px-6 max-w-7xl mx-auto relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-medium mb-6 backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <span>Autonomous Indian Macroeconomic Intelligence Platform</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.12] text-white">
            Decomposing India’s Economy into{' '}
            <span className="bg-gradient-to-r from-brand-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
              10 Collaborative Sector Agents
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            Macrograph-AI connects 10 domain AI agents over the <strong>Agent2Agent (A2A)</strong> reasoning protocol
            and <strong>FastMCP</strong> data layer. Uncover cross-sector transmission chains, query official 
            RBI DBIE & MoSPI data, and receive rigorous, <strong>strictly cited</strong> macroeconomic research.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={isAuthenticated ? onEnterWorkspace : onOpenAuth}
              className="w-full sm:w-auto py-3.5 px-8 rounded-xl bg-gradient-to-r from-brand-600 via-indigo-600 to-indigo-700 hover:from-brand-500 hover:to-indigo-600 text-white font-semibold text-base shadow-glow-brand transition-all flex items-center justify-center gap-2.5 group"
            >
              <span>{isAuthenticated ? 'Launch Research Workspace' : 'Sign in & Start Research'}</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="#sectors"
              className="w-full sm:w-auto py-3.5 px-6 rounded-xl glass-panel hover:bg-slate-800/80 text-slate-200 font-medium text-sm transition-all flex items-center justify-center gap-2"
            >
              <Layers className="w-4 h-4 text-brand-400" />
              <span>Explore 10 Sector Agents</span>
            </a>
          </div>

          {/* Real Data Highlights Banner */}
          <div className="mt-14 p-4 rounded-2xl glass-panel border border-white/10 max-w-4xl mx-auto shadow-2xl">
            <div className="text-xs uppercase tracking-wider font-mono text-slate-400 mb-3 flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Live Ingested RBI DBIE Benchmarks (Finance Sector)
              </span>
              <span>Updated Monthly & Fortnightly</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                <div className="text-xs text-slate-400">Non-Food Credit YoY</div>
                <div className="text-xl font-bold text-white mt-1">+13.0%</div>
                <div className="text-[11px] text-emerald-400 mt-0.5">₹217.96 Lakh Cr</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                <div className="text-xs text-slate-400">Gross NPA (SCBs)</div>
                <div className="text-xl font-bold text-white mt-1">2.8%</div>
                <div className="text-[11px] text-cyan-400 mt-0.5">Net NPA: 0.6%</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                <div className="text-xs text-slate-400">Capital Adequacy (CRAR)</div>
                <div className="text-xl font-bold text-white mt-1">16.8%</div>
                <div className="text-[11px] text-indigo-400 mt-0.5">CET-1: 13.9%</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                <div className="text-xs text-slate-400">Deposit Mobilisation</div>
                <div className="text-xl font-bold text-white mt-1">+11.8%</div>
                <div className="text-[11px] text-amber-400 mt-0.5">CD Ratio: 78.4%</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Dual Protocol Architecture Section */}
      <section id="architecture" className="py-20 border-t border-white/5 relative bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs uppercase font-mono tracking-widest text-brand-400 font-semibold mb-2">
              System Architecture
            </h2>
            <h3 className="text-3xl sm:text-4xl font-bold text-white">
              The Dual-Protocol Foundation: A2A vs FastMCP
            </h3>
            <p className="mt-3 text-slate-400 text-sm sm:text-base">
              Unlike generic LLM wrappers, Macrograph-AI enforces an architectural separation between agent reasoning
              and verified data retrieval.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* A2A Protocol */}
            <div className="p-8 rounded-2xl glass-panel-interactive border border-brand-500/20 relative group">
              <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center mb-6">
                <GitBranch className="w-6 h-6 text-brand-400" />
              </div>
              <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-brand-500/20 text-brand-300 mb-3">
                Agent ↔ Agent Reasoning Layer
              </div>
              <h4 className="text-xl font-bold text-white">A2A Protocol (Agent2Agent)</h4>
              <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                Empowers sector agents to deliberate, delegate analytical subtasks, challenge peer assumptions, and pass
                causal findings. <strong>No raw data is ever fetched via A2A</strong> — it strictly handles economic logic,
                transmission paths, and hypothesis testing.
              </p>
              <ul className="mt-5 space-y-2 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                  <span>Agent Card discovery & dynamic coalition assembly</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                  <span>Single Source of Truth per indicator (no double counting)</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                  <span>Cross-sector transmission chain coordination</span>
                </li>
              </ul>
            </div>

            {/* FastMCP Data Layer */}
            <div className="p-8 rounded-2xl glass-panel-interactive border border-accent-cyan/20 relative group">
              <div className="w-12 h-12 rounded-xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center mb-6">
                <Database className="w-6 h-6 text-accent-cyan" />
              </div>
              <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-accent-cyan/20 text-cyan-300 mb-3">
                Agent ↔ Data Retrieval Layer
              </div>
              <h4 className="text-xl font-bold text-white">FastMCP Tool Servers</h4>
              <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                Each sector agent runs an isolated <strong>FastMCP server</strong> connected to authorized government and
                financial mirrors (RBI DBIE, MoSPI, Agmarknet). Outbound HTTP queries are wrapped with Tenacity retries
                and cached in sector-dedicated DuckDB stores.
              </p>
              <ul className="mt-5 space-y-2 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>Direct endpoints for RBI Form A, Key Rates & FSR tables</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>DuckDB local columnar storage for zero latency queries</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>Strict cryptographic provenance hash on every fetched cell</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Non-Negotiable Anti-Hallucination Policy */}
      <section id="citation-policy" className="py-20 border-t border-white/5 relative">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center mx-auto mb-6 shadow-glow-emerald">
            <ShieldCheck className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-xs uppercase font-mono tracking-widest text-emerald-400 font-semibold mb-2">
            Non-Negotiable Rule
          </h2>
          <h3 className="text-3xl sm:text-4xl font-bold text-white">
            "No Source, No Answer" Anti-Hallucination Policy
          </h3>
          <p className="mt-4 text-slate-300 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            Financial decision-making demands absolute integrity. In Macrograph-AI, agents are strictly forbidden from
            generating, guessing, or hardcoding plausible-sounding figures.
          </p>

          <div className="mt-10 grid sm:grid-cols-3 gap-6 text-left">
            <div className="p-5 rounded-xl glass-panel border border-white/5">
              <div className="text-brand-400 font-semibold text-sm mb-1">1. Mandatory Chain</div>
              <p className="text-xs text-slate-400 leading-normal">
                Every claim must state the <strong>source agent</strong>, the <strong>MCP tool</strong>, and official
                table reference.
              </p>
            </div>
            <div className="p-5 rounded-xl glass-panel border border-white/5">
              <div className="text-brand-400 font-semibold text-sm mb-1">2. Zero Hallucination</div>
              <p className="text-xs text-slate-400 leading-normal">
                If official data cannot be retrieved from an authorized mirror, the agent explicitly returns{' '}
                <code className="text-rose-400">status: unavailable</code>.
              </p>
            </div>
            <div className="p-5 rounded-xl glass-panel border border-white/5">
              <div className="text-brand-400 font-semibold text-sm mb-1">3. Verified Attributions</div>
              <p className="text-xs text-slate-400 leading-normal">
                Each observation includes observation period, freshness flag (<code className="text-emerald-400">live</code> or{' '}
                <code className="text-amber-400">cached</code>), and SHA-256 hash.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 10 Sector Agents Showcase */}
      <section id="sectors" className="py-20 border-t border-white/5 bg-slate-950/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12">
            <div>
              <h2 className="text-xs uppercase font-mono tracking-widest text-brand-400 font-semibold mb-2">
                Domain Specialization
              </h2>
              <h3 className="text-3xl sm:text-4xl font-bold text-white">
                The 10 Macroeconomic Sector Agents
              </h3>
              <p className="mt-2 text-slate-400 text-sm max-w-xl">
                Every indicator has exactly one owner agent. The Finance Sector is live with RBI DBIE DuckDB integration;
                other sectors are staged or in active development.
              </p>
            </div>

            <div className="mt-4 md:mt-0 flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span className="text-slate-300">Live Active</span>
              </span>
              <span className="flex items-center gap-1.5 ml-3">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                <span className="text-slate-300">Staged</span>
              </span>
              <span className="flex items-center gap-1.5 ml-3">
                <span className="w-2 h-2 rounded-full bg-slate-600" />
                <span className="text-slate-400">In Development</span>
              </span>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {SECTOR_AGENTS.map((agent) => {
              const isLive = agent.status === 'active';
              const isStaged = agent.status === 'staged';

              return (
                <div
                  key={agent.id}
                  className={`p-6 rounded-2xl glass-panel relative border transition-all ${
                    isLive
                      ? 'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50 shadow-glow-emerald/20'
                      : isStaged
                      ? 'border-cyan-500/20 bg-cyan-950/5 hover:border-cyan-500/40'
                      : 'border-white/5 opacity-70 hover:opacity-90'
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm"
                      style={{ backgroundColor: `${agent.color}15`, color: agent.color, border: `1px solid ${agent.color}30` }}
                    >
                      {agent.name.slice(0, 2).toUpperCase()}
                    </div>
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-semibold ${
                        isLive
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : isStaged
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {isLive ? '● Live Connected' : isStaged ? '○ Staged' : 'Planned'}
                    </span>
                  </div>

                  <h4 className="font-semibold text-white text-base flex items-center gap-2">
                    {agent.name}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{agent.domain}</p>

                  <div className="mt-4 pt-3 border-t border-white/5 space-y-1.5">
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span className="text-slate-500">Authority:</span>
                      <span className="font-medium text-slate-300 truncate max-w-[180px]">{agent.authority}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span className="text-slate-500">Key Indicators:</span>
                      <span className="font-medium text-slate-300 truncate max-w-[180px]">
                        {agent.ownership.slice(0, 2).join(', ')}
                      </span>
                    </div>
                  </div>

                  {isLive && (
                    <button
                      onClick={isAuthenticated ? onEnterWorkspace : onOpenAuth}
                      className="mt-4 w-full py-2 px-3 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
                    >
                      <span>Direct Chat & Real Analytics</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-10 bg-slate-950 text-slate-400 text-xs">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-brand-400" />
            <span className="text-slate-200 font-semibold">Macrograph-AI</span>
            <span>— Indian Macroeconomic Intelligence Platform</span>
          </div>
          <div>
            Built with FastAPI, FastMCP, LangGraph, DuckDB, Groq Llama-3.3 & React 18
          </div>
        </div>
      </footer>
    </div>
  );
};
