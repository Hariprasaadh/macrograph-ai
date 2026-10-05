import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Network,
  ArrowRight,
  Database,
  Sparkles,
  Layers,
  GitBranch,
  Terminal,
  Globe,
  TrendingUp,
  Landmark,
  Zap,
  CheckCircle2,
  ChevronRight,
  Activity,
  Receipt,
  Menu,
  X,
} from 'lucide-react';
import { SECTOR_AGENTS } from '../data/agents';
import { ParallaxHero } from './motion/ParallaxHero';
import { Marquee3D } from './motion/Marquee3D';
import { TiltCard } from './motion/TiltCard';
import { useGsapPage, useScrollProgress } from '../hooks/useGsapPage';

// UI-only scroll reveal: transform/opacity, respects reduced-motion, no data logic
const useRevealOnScroll = () => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      root.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const els = root.querySelectorAll('.reveal');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return ref;
};

const HERO_ROTATING = [
  'Indian Macroeconomics.',
  'Fiscal & Sovereign Debt.',
  'Policy Transmission.',
  'Banking Telemetry.',
  'Cross-Sector Shocks.',
];

const TRUST_STRIP = [
  'RBI DBIE Official Mirrors',
  'Ministry of Finance Union Budget',
  'MoSPI eSankhyiki FastMCP',
  'IMF SDMX 3.0 WEO & BPM6',
  'GST Council Monthly Revenue',
  'NSE Market Telemetry',
  'DuckDB Columnar Persistence',
  'A2A Protocol Reasoning Mesh',
  'Zero Hallucination Standard',
];


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
  const [activeConsoleTab, setActiveConsoleTab] = useState<'mesh' | 'gateways' | 'terminal'>('mesh');
  const [selectedTerminalQuery, setSelectedTerminalQuery] = useState<number>(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [heroIndex, setHeroIndex] = useState(0);
  const revealRef = useRevealOnScroll();
  const progressRef = useRef<HTMLDivElement>(null);
  useGsapPage(revealRef);
  useScrollProgress(progressRef);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const t = setInterval(() => setHeroIndex((i) => (i + 1) % HERO_ROTATING.length), 3200);
    return () => clearInterval(t);
  }, []);

  const onConsoleKeyDown = (e: React.KeyboardEvent) => {
    const order: Array<'mesh' | 'gateways' | 'terminal'> = ['mesh', 'gateways', 'terminal'];
    const idx = order.indexOf(activeConsoleTab);
    if (e.key === 'ArrowRight') setActiveConsoleTab(order[(idx + 1) % order.length]);
    if (e.key === 'ArrowLeft') setActiveConsoleTab(order[(idx + order.length - 1) % order.length]);
  };

  const terminalQueries = [
    {
      title: "Repo Rate Transmission Chain",
      query: "Analyze transmission of a 25 bps Repo Rate cut through Scheduled Commercial Banks to retail credit and inflation.",
      agents: ["Monetary Sector", "Finance Sector", "Prices Sector"],
      sources: ["RBI DBIE r531 (Key Rates)", "RBI r539 (Bank Credit)", "MoSPI CPI Combined"],
      latency: "340ms",
      confidence: "99.4%",
      summary: "A 25 bps cut in the repo rate typically transmits with a 2-4 month lag to fresh rupee WALR (currently 9.38%). Commercial banks reduce MCLR margins, stimulating non-food credit growth (currently +13.0% YoY). Prices sector indicates a 15-20 bps rebound in core inflation over 3 quarters.",
    },
    {
      title: "Forex Reserves & BoP Deficit Cover",
      query: "Assess India's Balance of Payments sustainability and Forex Reserve import adequacy under high crude import prices.",
      agents: ["External Sector", "Monetary Sector", "Real Sector"],
      sources: ["RBI DBIE r574 (Forex Reserves)", "IMF SDMX 3.0 (BOP BPM6)", "Yahoo Finance (Brent Spot)"],
      latency: "410ms",
      confidence: "99.1%",
      summary: "Forex reserves stand at $704.8 Billion (13.2 months import cover). IMF SDMX quarterly BoP confirms current account deficit contained at -1.1% of GDP for FY26. Robust invisibles surplus ($42.1B/quarter) and software receipts heavily cushion elevated oil import bills.",
    },
    {
      title: "Banking Asset Quality & Solvency",
      query: "Evaluate SCB Gross NPA trajectories and Capital Adequacy (CRAR) buffer across public and private banks.",
      agents: ["Finance Sector", "Capital Markets"],
      sources: ["RBI DBIE r330 (GNPA/NNPA)", "RBI r329 (CRAR)", "NSE Bank Nifty"],
      latency: "290ms",
      confidence: "99.8%",
      summary: "SCB Gross NPA ratio dropped to a multi-decade low of 2.8% (Net NPA: 0.6%) with Provision Coverage Ratio (PCR) at 76.4%. CRAR at 16.8% provides a strong 530 bps safety buffer above Basel III norms. Bank Nifty trades at resilient multiples with Nifty Bank at 54,450.",
    },
    {
      title: "Union Fiscal Deficit & Capex Push",
      query: "Assess India's Union Gross Fiscal Deficit consolidation target (4.9% of GDP) and public capital expenditure execution.",
      agents: ["Fiscal Sector", "Real Sector", "Monetary Sector"],
      sources: ["Union Budget 2024-25 (CGA Statement 1)", "IMF WEO IND.GGXWDG_NGDP.A", "MoSPI Net Product Taxes"],
      latency: "320ms",
      confidence: "99.7%",
      summary: "Union Fiscal Deficit for FY 2024-25 is targeted at ₹16.12 Lakh Cr (4.9% of GDP, consolidating towards <4.5% by FY26). Capex allocation surged to ₹11.11 Lakh Cr (+17% YoY), driving infrastructure multiplier effects. Gross monthly GST revenue averages ₹1.82 Lakh Cr with 10.2% buoyancy. General Government debt stands at 84.78% of GDP with sustainable primary deficit dynamics.",
    },
  ];

  return (
    <div ref={revealRef} className="min-h-screen bg-background text-slate-100 relative overflow-hidden bg-grid-pattern selection:bg-brand-500/30 selection:text-cyan-200">
      <div ref={progressRef} className="scrolly-progress" aria-hidden="true" />
      <a href="#main-hero" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-cyan-500 focus:text-black focus:text-sm focus:font-semibold">
        Skip to content
      </a>
      {/* Ambient parallax depth layers (decorative only) */}
      <ParallaxHero />

      {/* Announcement bar — UI only */}
      <div className="relative z-50 bg-gradient-to-r from-brand-600/20 via-cyan-500/15 to-brand-600/20 border-b border-white/[0.08]">
        <div className="max-w-7xl mx-auto px-6 py-2 flex items-center justify-center gap-2.5 text-[11px] sm:text-xs font-mono text-cyan-200">
          <Sparkles className="w-3.5 h-3.5 text-cyan-300 shrink-0" aria-hidden="true" />
          <span className="truncate">Live official macro telemetry, cited down to the table</span>
          <a href="#console" className="shrink-0 inline-flex items-center gap-1 font-semibold text-white hover:text-cyan-200 transition-colors">
            <span>Read more</span>
            <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
          </a>
        </div>
      </div>

      {/* Top navigation */}
      <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-background/80 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          {/* Logo & Beacon */}
          <div className="flex items-center gap-3.5">
            <div className="relative group cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-cyan-500 to-indigo-500 p-[1px] shadow-glow-brand group-hover:shadow-glow-cyan transition-all duration-300">
                <div className="w-full h-full bg-[#060b18] rounded-[11px] flex items-center justify-center">
                  <Network className="w-5 h-5 text-brand-400 group-hover:text-cyan-300 transition-colors" />
                </div>
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-tight text-white">
                  Macrograph<span className="text-brand-400">.AI</span>
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 flex items-center gap-1.5 shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  10 Nodes Active
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono tracking-tight">
                Autonomous Multi-Agent Indian Macro Intelligence
              </div>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="hidden lg:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#console" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-brand-400" />
              <span>Architecture Console</span>
            </a>
            <a href="#protocols" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
              <span>Dual-Protocol Mesh</span>
            </a>
            <a href="#sectors" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <span>10 Sector Agents</span>
            </a>
            <a href="#governance" className="hover:text-cyan-300 transition-colors flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
              <span>Citation Guarantee</span>
            </a>
          </nav>

          {/* CTAs */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => setMobileNavOpen((v) => !v)}
              aria-expanded={mobileNavOpen}
              aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
              className="lg:hidden touch-44 p-2.5 rounded-xl border border-white/10 text-slate-200 hover:border-cyan-400/40 hover:text-white transition-colors flex items-center justify-center"
            >
              {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            {isAuthenticated ? (
              <button
                onClick={onEnterWorkspace}
                className="touch-44 py-2.5 px-4 sm:px-5 rounded-xl bg-gradient-to-r from-brand-600 via-indigo-600 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white font-semibold text-sm shadow-glow-brand hover:shadow-glow-cyan transition-all flex items-center gap-2 group"
              >
                <span>Launch Hub</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <button
                onClick={onOpenAuth}
                className="touch-44 py-2.5 px-4 sm:px-5 rounded-xl bg-surface-mesh border border-white/10 hover:border-brand-400/40 text-white font-medium text-sm transition-all flex items-center gap-2.5 shadow-lg hover:shadow-glow-brand group"
              >
                <svg viewBox="0 0 24 24" className="w-4 h-4 shrink-0">
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
        {/* Mobile nav drawer — UI only */}
        {mobileNavOpen && (
          <nav aria-label="Mobile" className="lg:hidden border-t border-white/[0.08] bg-[#050b1a]/95 backdrop-blur-2xl px-6 py-4 flex flex-col gap-1 text-sm font-medium text-slate-200">
            <a href="#console" onClick={() => setMobileNavOpen(false)} className="touch-44 flex items-center gap-2.5 px-3 rounded-xl hover:bg-white/5"> <Terminal className="w-4 h-4 text-brand-400" /> Architecture Console </a>
            <a href="#protocols" onClick={() => setMobileNavOpen(false)} className="touch-44 flex items-center gap-2.5 px-3 rounded-xl hover:bg-white/5"> <GitBranch className="w-4 h-4 text-indigo-400" /> Dual-Protocol Mesh </a>
            <a href="#sectors" onClick={() => setMobileNavOpen(false)} className="touch-44 flex items-center gap-2.5 px-3 rounded-xl hover:bg-white/5"> <Layers className="w-4 h-4 text-emerald-400" /> 10 Sector Agents </a>
            <a href="#governance" onClick={() => setMobileNavOpen(false)} className="touch-44 flex items-center gap-2.5 px-3 rounded-xl hover:bg-white/5"> <ShieldCheck className="w-4 h-4 text-cyan-400" /> Citation Guarantee </a>
          </nav>
        )}
      </header>

      {/* Hero Section */}
      <section id="main-hero" className="pt-16 sm:pt-24 pb-16 sm:pb-20 px-6 max-w-7xl mx-auto relative z-10 text-center">
        {/* Pill announcement badge */}
        <div data-entrance className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full mesh-glow-pill text-cyan-300 text-xs font-mono font-medium mb-8 backdrop-blur-xl">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" />
          <span>FAST-MCP & A2A DUAL-PROTOCOL MESH • ZERO HALLUCINATION GUARANTEE</span>
          <ChevronRight className="w-3.5 h-3.5 text-cyan-400" />
        </div>

        {/* Headline with rotating line — UI only */}
        <h1 data-entrance className="reveal mesh-headline font-extrabold max-w-5xl mx-auto text-white">
          The Autonomous AI Mesh for{' '}
          <span className="mesh-gradient-text" aria-live="polite">
            {HERO_ROTATING[heroIndex]}
          </span>
        </h1>
        <div className="mt-4 flex items-center justify-center gap-1.5" aria-hidden="true">
          {HERO_ROTATING.map((_, i) => (
            <span key={i} className={`h-1.5 rounded-full transition-all duration-500 ${i === heroIndex ? 'w-8 bg-cyan-400' : 'w-1.5 bg-white/20'}`} />
          ))}
        </div>

        {/* Subtitle */}
        <p data-entrance className="mt-8 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
          Macrograph-AI connects <strong>10 specialized sector agents</strong> over the <strong>A2A cognitive reasoning protocol</strong> and <strong>FastMCP data gateways</strong>. Directly query live official RBI DBIE, MoSPI, IMF SDMX 3.0, and Yahoo Finance feeds with strict citation guarantees.
        </p>

        {/* CTAs */}
        <div data-entrance className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={isAuthenticated ? onEnterWorkspace : onOpenAuth}
            className="touch-44 w-full sm:w-auto py-4 px-9 rounded-2xl bg-gradient-to-r from-brand-500 via-indigo-600 to-cyan-500 hover:from-brand-400 hover:to-cyan-400 text-white font-bold text-base shadow-glow-brand transition-all flex items-center justify-center gap-3 group"
          >
            <span>{isAuthenticated ? 'Open Research Workspace' : 'Get Started with Google'}</span>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
          </button>
          <a
            href="#console"
            className="touch-44 w-full sm:w-auto py-4 px-8 rounded-2xl glass-panel hover:bg-slate-800/80 text-slate-200 font-semibold text-sm transition-all flex items-center justify-center gap-2.5 border border-white/10 hover:border-cyan-400/40"
          >
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Interactive Architecture Console</span>
          </a>
        </div>

        {/* Numbered journey — outcome path, anchors only, UI only */}
        <nav aria-label="How a question becomes a cited answer" className="mt-8 flex justify-center px-2">
          <ol className="inline-flex max-w-full items-stretch gap-1.5 p-1.5 rounded-2xl bg-slate-900/80 border border-white/10 backdrop-blur-xl overflow-x-auto">
            {[
              { n: '01', label: 'Ask', desc: 'Any macro question', href: '#console' },
              { n: '02', label: 'Trace', desc: 'Follow the shock path', href: '#sectors' },
              { n: '03', label: 'Verify', desc: 'Check every citation', href: '#governance' },
            ].map((s) => (
              <li key={s.n}>
                <a href={s.href} className="touch-44 flex items-center gap-2.5 px-4 sm:px-5 rounded-xl hover:bg-white/5 transition-colors text-left whitespace-nowrap">
                  <span className="text-[11px] font-mono font-bold text-cyan-300">{s.n}</span>
                  <span>
                    <span className="block text-xs font-semibold text-white">{s.label}</span>
                    <span className="block text-[10px] text-slate-500 font-mono">{s.desc}</span>
                  </span>
                </a>
              </li>
            ))}
          </ol>
        </nav>

        {/* Authority marquee — dual-row 3D perspective, transform only, UI only */}
        <Marquee3D items={TRUST_STRIP} />

        {/* Telemetry metrics strip — 3D tilt depth cards */}
        <div className="reveal mt-12 sm:mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 max-w-7xl mx-auto text-left">
          <TiltCard label="Fiscal deficit telemetry" maxTilt={6}>
          <div className="p-5 rounded-2xl mesh-card text-left h-full border border-pink-500/20 shadow-[0_0_25px_rgba(236,72,153,0.1)]">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Union Fiscal Deficit</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-pink-500/10 text-pink-300 border border-pink-500/20">MoF / CGA</span>
            </div>
            <div className="text-3xl font-extrabold text-white mt-2 font-mono">4.9%</div>
            <div className="text-xs text-pink-400 mt-1 flex items-center gap-1">
              <Receipt className="w-3.5 h-3.5" />
              <span>₹16.12L Cr BE • GST ₹1.82L Cr</span>
            </div>
          </div>
          </TiltCard>

          <TiltCard label="Non-food credit telemetry" maxTilt={6}>
          <div className="p-5 rounded-2xl mesh-card text-left h-full">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Non-Food Credit YoY</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">RBI r539</span>
            </div>
            <div className="text-3xl font-extrabold text-white mt-2 font-mono">+13.0%</div>
            <div className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>₹217.96 Lakh Cr Deployed</span>
            </div>
          </div>
          </TiltCard>

          <TiltCard label="Asset quality telemetry" maxTilt={6}>
          <div className="p-5 rounded-2xl mesh-card text-left h-full">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Gross NPA Ratio</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">SCBs FSR</span>
            </div>
            <div className="text-3xl font-extrabold text-white mt-2 font-mono">2.8%</div>
            <div className="text-xs text-cyan-300 mt-1 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Net NPA 0.6% • Multi-Decade Low</span>
            </div>
          </div>
          </TiltCard>

          <TiltCard label="Forex reserves telemetry" maxTilt={6}>
          <div className="p-5 rounded-2xl mesh-card text-left h-full">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Foreign Exchange Reserves</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-500/10 text-brand-300 border border-brand-500/20">Weekly r574</span>
            </div>
            <div className="text-3xl font-extrabold text-white mt-2 font-mono">$704.8B</div>
            <div className="text-xs text-brand-300 mt-1 flex items-center gap-1">
              <Globe className="w-3.5 h-3.5" />
              <span>13.2 Months Import Cover</span>
            </div>
          </div>
          </TiltCard>

          <TiltCard label="Capital adequacy telemetry" maxTilt={6}>
          <div className="p-5 rounded-2xl mesh-card text-left h-full">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Capital Adequacy (CRAR)</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">RBI r329</span>
            </div>
            <div className="text-3xl font-extrabold text-white mt-2 font-mono">16.8%</div>
            <div className="text-xs text-indigo-300 mt-1 flex items-center gap-1">
              <Activity className="w-3.5 h-3.5" />
              <span>CET-1: 13.9% (+530 bps Buffer)</span>
            </div>
          </div>
          </TiltCard>
        </div>

        {/* Sample resolver teaser — local state only, no backend calls */}
        <div className="reveal mt-10 max-w-5xl mx-auto text-left rounded-3xl border border-white/10 bg-white/[0.02] backdrop-blur-xl p-5 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <p className="mesh-eyebrow text-cyan-300">_See what the mesh would cite_</p>
              <p className="text-sm text-slate-300 mt-1.5">Pick a sample question to preview its coalition, sources, and cited answer below.</p>
            </div>
            <span className="text-[11px] font-mono text-slate-500 shrink-0">3 samples • no sign-in needed</span>
          </div>
          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {terminalQueries.map((q, idx) => (
              <button
                key={q.title}
                type="button"
                onClick={() => {
                  setSelectedTerminalQuery(idx);
                  setActiveConsoleTab('terminal');
                  document.getElementById('console')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                aria-label={`Preview sample: ${q.title}`}
                title={q.query}
                className={`touch-44 shrink-0 max-w-[280px] truncate px-4 py-2.5 rounded-xl border text-xs font-medium transition-all ${
                  selectedTerminalQuery === idx
                    ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-200'
                    : 'bg-slate-900/60 border-white/10 text-slate-300 hover:text-white hover:border-cyan-400/30'
                }`}
              >
                {q.title}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Before/after comparison — UI only */}
      <section aria-label="The fragmentation challenge" className="reveal py-16 sm:py-24 border-t border-white/[0.08] relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <p className="mesh-eyebrow text-cyan-400 mb-3">_The challenge_</p>
            <h2 className="mesh-section-title font-extrabold text-white">Scattered figures slow down good macro calls</h2>
            <p className="mt-4 text-slate-400 text-sm sm:text-base">Bring every release, table, and vintage into one cited workspace.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-4 sm:gap-6">
            <div className="mesh-compare-before rounded-3xl p-6 sm:p-8">
              <p className="mesh-eyebrow text-rose-300 mb-4">The old way</p>
              <ul className="space-y-3 text-sm text-slate-300">
                <li className="flex gap-2.5"><span aria-hidden="true" className="text-rose-400">✕</span><span>Scattered RBI PDFs, mismatched periods, copy-pasted figures</span></li>
                <li className="flex gap-2.5"><span aria-hidden="true" className="text-rose-400">✕</span><span>One model guessing across GDP, inflation, forex, and banking</span></li>
                <li className="flex gap-2.5"><span aria-hidden="true" className="text-rose-400">✕</span><span>No citation chain — numbers without tables or vintages</span></li>
              </ul>
            </div>
            <div className="mesh-compare-after mesh-beam wobble-hover rounded-3xl p-6 sm:p-8">
              <p className="mesh-eyebrow text-cyan-300 mb-4">The Macrograph way</p>
              <ul className="space-y-3 text-sm text-slate-200">
                <li className="flex gap-2.5"><CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" /><span>10 owner-agents, one source of truth per indicator</span></li>
                <li className="flex gap-2.5"><CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" /><span>A2A deliberation + FastMCP retrieval with DuckDB cache</span></li>
                <li className="flex gap-2.5"><CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" /><span>Every claim carries agent, table, period, and freshness</span></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 grid sm:grid-cols-3 gap-4 text-left">
            <div className="p-6 rounded-2xl mesh-card"><p className="font-bold text-white text-sm">Move fast</p><p className="text-xs text-slate-400 mt-1.5 leading-relaxed">Route any macro question across all 10 sectors in one workspace.</p></div>
            <div className="p-6 rounded-2xl mesh-card"><p className="font-bold text-white text-sm">Stay accurate</p><p className="text-xs text-slate-400 mt-1.5 leading-relaxed">Block guessed figures with the no-source-no-answer bar.</p></div>
            <div className="p-6 rounded-2xl mesh-card"><p className="font-bold text-white text-sm">Reuse everything</p><p className="text-xs text-slate-400 mt-1.5 leading-relaxed">Carry verified telemetry across research, risk, and policy notes.</p></div>
          </div>
        </div>
      </section>

      {/* Interactive architecture showcase */}
      <section id="console" className="py-20 border-t border-white/[0.08] relative bg-[#050b1a]/70">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <p className="mesh-eyebrow text-cyan-400 mb-3 flex items-center justify-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              <span>_Interactive architecture console_</span>
            </p>
            <h2 className="mesh-section-title font-extrabold text-white">
              Designed for Speed, Governance &amp; Provenance
            </h2>
            <p className="mt-4 text-slate-400 text-sm sm:text-base">
              Explore how the multi-agent mesh routes queries, triggers FastMCP retrieval gateways, and synthesizes institutional-grade research.
            </p>
          </div>

          {/* Tab selector — accessible tablist, UI only */}
          <div className="flex items-center justify-center gap-2 mb-8 px-2">
            <div role="tablist" aria-label="Architecture console views" onKeyDown={onConsoleKeyDown} className="p-1.5 rounded-2xl bg-slate-900/90 border border-white/10 flex items-center gap-1 backdrop-blur-xl max-w-full overflow-x-auto">
              <button
                role="tab" aria-selected={activeConsoleTab === 'mesh'} aria-controls="console-panel" id="console-tab-mesh"
                onClick={() => setActiveConsoleTab('mesh')}
                className={`touch-44 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs font-semibold font-mono transition-all whitespace-nowrap ${
                  activeConsoleTab === 'mesh'
                    ? 'bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-glow-cyan'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Network className="w-4 h-4" />
                <span>1. Multi-Agent A2A Mesh</span>
              </button>
              <button
                role="tab" aria-selected={activeConsoleTab === 'gateways'} aria-controls="console-panel" id="console-tab-gateways"
                onClick={() => setActiveConsoleTab('gateways')}
                className={`touch-44 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs font-semibold font-mono transition-all whitespace-nowrap ${
                  activeConsoleTab === 'gateways'
                    ? 'bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-glow-cyan'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Database className="w-4 h-4" />
                <span>2. FastMCP Data Gateways</span>
              </button>
              <button
                role="tab" aria-selected={activeConsoleTab === 'terminal'} aria-controls="console-panel" id="console-tab-terminal"
                onClick={() => setActiveConsoleTab('terminal')}
                className={`touch-44 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-xs font-semibold font-mono transition-all whitespace-nowrap ${
                  activeConsoleTab === 'terminal'
                    ? 'bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-glow-cyan'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Terminal className="w-4 h-4" />
                <span>3. Live Research Terminal</span>
              </button>
            </div>
          </div>

          {/* Console Viewport — scrollytelling step */}
          <div id="console-panel" role="tabpanel" aria-labelledby={`console-tab-${activeConsoleTab}`} className="reveal scrolly-step p-4 sm:p-6 md:p-8 rounded-3xl mesh-card mesh-beam border border-white/10 shadow-2xl relative overflow-hidden">
            {/* Ambient edge highlight */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

            {/* TAB 1: Multi-Agent A2A Mesh */}
            {activeConsoleTab === 'mesh' && (
              <div className="space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/10">
                  <div>
                    <h4 className="text-xl font-bold text-white flex items-center gap-2">
                      <span>Decentralized A2A Protocol Reasoning Layer</span>
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      No agent computes indicators outside its domain. Deliberation, causal paths, and shock propagation flow across standardized Agent Cards.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs text-cyan-300 bg-cyan-500/10 px-3 py-1.5 rounded-xl border border-cyan-500/20">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Single Source of Truth per Indicator</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
                  {SECTOR_AGENTS.map((agent) => (
                    <div
                      key={agent.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.06] hover:border-cyan-500/40 transition-all group"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs" style={{ backgroundColor: `${agent.color}20`, color: agent.color }}>
                          {agent.name.slice(0, 2).toUpperCase()}
                        </span>
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: agent.status === 'active' ? '#00e599' : '#00c9ff' }} />
                      </div>
                      <div className="font-semibold text-white text-xs truncate group-hover:text-cyan-300 transition-colors">{agent.name}</div>
                      <div className="text-[10px] text-slate-400 truncate mt-0.5">{agent.authority}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 2: FastMCP Data Gateways */}
            {activeConsoleTab === 'gateways' && (
              <div className="space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/10">
                  <div>
                    <h4 className="text-xl font-bold text-white flex items-center gap-2">
                      <span>Unified FastMCP Ingestion Gateways</span>
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      5 Isolated data retrieval pipelines running over FastMCP with Tenacity retries and DuckDB columnar persistence.
                    </p>
                  </div>
                  <div className="font-mono text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20 flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Zero Authentication • High Availability</span>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.06] space-y-3">
                    <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold font-mono">
                      <Landmark className="w-4 h-4" />
                      <span>RBI DBIE Gateway</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      340+ official central bank tables covering Scheduled Commercial Banks, policy rates, daily LAF, and money stock components.
                    </p>
                    <div className="text-[11px] font-mono text-slate-500">Endpoints: r531, r539, r330, r574, r689</div>
                  </div>

                  <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.06] space-y-3">
                    <div className="flex items-center gap-2 text-pink-400 text-sm font-semibold font-mono">
                      <Receipt className="w-4 h-4" />
                      <span>MoSPI eSankhyiki FastMCP</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Official FastMCP gateway to National Accounts (NAS) Net Taxes on Products, Government Consumption, and IIP series.
                    </p>
                    <div className="text-[11px] font-mono text-slate-500">Server: mcp.mospi.gov.in (NAS Ind 2)</div>
                  </div>

                  <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.06] space-y-3">
                    <div className="flex items-center gap-2 text-indigo-400 text-sm font-semibold font-mono">
                      <Globe className="w-4 h-4" />
                      <span>IMF SDMX 3.0 & WEO</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      General Government Gross Debt % of GDP, Net Lending/Borrowing, and World Economic Outlook medium-term fiscal projections.
                    </p>
                    <div className="text-[11px] font-mono text-slate-500">Protocol: SDMX 3.0 • IND.GGXWDG</div>
                  </div>

                  <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.06] space-y-3">
                    <div className="flex items-center gap-2 text-brand-400 text-sm font-semibold font-mono">
                      <Zap className="w-4 h-4" />
                      <span>eco-policy & MoF PIB</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Statutory GST slab calculator, mod-36 GSTIN checksum validation, and real-time Ministry of Finance PIB news intelligence.
                    </p>
                    <div className="text-[11px] font-mono text-slate-500">Feeds: eco-policy-mcp, Tavily PIB</div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: Live Research Terminal */}
            {activeConsoleTab === 'terminal' && (
              <div className="space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/10">
                  <div>
                    <h4 className="text-xl font-bold text-white flex items-center gap-2 font-mono">
                      <span>$ macrograph-query --consensus</span>
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      Select a sample query to see how the multi-agent mesh deconstructs questions and attributes official sources.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {terminalQueries.map((_, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedTerminalQuery(idx)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                          selectedTerminalQuery === idx
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                            : 'bg-slate-900 text-slate-400 hover:text-white border border-white/5'
                        }`}
                      >
                        Sample #{idx + 1}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-[#030612] border border-cyan-500/30 font-mono text-xs space-y-4">
                  <div className="flex items-center justify-between border-b border-white/10 pb-3 text-slate-400">
                    <div className="flex items-center gap-2 text-cyan-400">
                      <Terminal className="w-4 h-4" />
                      <span className="font-semibold">{terminalQueries[selectedTerminalQuery].title}</span>
                    </div>
                    <div className="flex items-center gap-4 text-[11px]">
                      <span>Latency: <strong className="text-emerald-400">{terminalQueries[selectedTerminalQuery].latency}</strong></span>
                      <span>Confidence: <strong className="text-cyan-400">{terminalQueries[selectedTerminalQuery].confidence}</strong></span>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500">QUERY: </span>
                    <span className="text-slate-200">"{terminalQueries[selectedTerminalQuery].query}"</span>
                  </div>

                  <div className="grid md:grid-cols-2 gap-3 pt-2">
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">A2A Coalition Assembly</div>
                      <div className="flex flex-wrap gap-1.5">
                        {terminalQueries[selectedTerminalQuery].agents.map((ag, i) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 text-[11px] border border-brand-500/30">
                            {ag}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">FastMCP Mirrors Ingested</div>
                      <div className="flex flex-wrap gap-1.5">
                        {terminalQueries[selectedTerminalQuery].sources.map((src, i) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[11px] border border-emerald-500/20">
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 text-slate-300 leading-relaxed bg-slate-900/40 p-4 rounded-xl border border-white/5 font-sans text-xs">
                    <div className="text-[10px] text-cyan-400 font-mono uppercase tracking-wider mb-1 font-semibold">Attributed Synthesis Output</div>
                    {terminalQueries[selectedTerminalQuery].summary}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Dual Protocol Architecture Section */}
      <section id="protocols" className="py-24 border-t border-white/[0.08] relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <p className="mesh-eyebrow text-brand-400 mb-3">_The platform_</p>
            <h2 className="mesh-section-title font-extrabold text-white">
              A2A Reasoning vs FastMCP Data Layer
            </h2>
            <p className="mt-3 text-slate-400 text-sm sm:text-base">
              Architecturally separating cognitive cross-sector collaboration from authoritative data retrieval.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* A2A Protocol Card */}
            <div className="reveal-gsap p-8 rounded-3xl mesh-card wobble-hover border border-brand-500/20 relative group hover:border-brand-500/40 transition-all">
              <div className="w-12 h-12 rounded-2xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center mb-6 shadow-glow-brand">
                <GitBranch className="w-6 h-6 text-brand-400" />
              </div>
              <p className="mesh-eyebrow text-brand-300/80 mb-3">_01/ Agent ↔ Agent reasoning_</p>
              <h4 className="text-2xl font-bold text-white">A2A Protocol Mesh</h4>
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                Empowers sector agents to deliberate, delegate analytical subtasks, challenge peer assumptions, and pass
                causal findings. <strong>No raw data is ever fetched via A2A</strong> — it strictly handles economic logic,
                transmission paths, and hypothesis testing.
              </p>
              <ul className="mt-6 space-y-2.5 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0" />
                  <span>Agent Card discovery & dynamic coalition assembly</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0" />
                  <span>Single Source of Truth per indicator (no double counting)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0" />
                  <span>Cross-sector transmission chain coordination</span>
                </li>
              </ul>
            </div>

            {/* FastMCP Data Layer Card */}
            <div className="reveal-gsap p-8 rounded-3xl mesh-card wobble-hover border border-cyan-500/20 relative group hover:border-cyan-500/40 transition-all">
              <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-6 shadow-glow-cyan">
                <Database className="w-6 h-6 text-cyan-400" />
              </div>
              <p className="mesh-eyebrow text-cyan-300/80 mb-3">_02/ Agent ↔ Data retrieval_</p>
              <h4 className="text-2xl font-bold text-white">FastMCP Tool Servers</h4>
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                Each sector agent runs an isolated <strong>FastMCP server</strong> connected to authorized government and
                financial mirrors (RBI DBIE, MoSPI, IMF SDMX 3.0, Yahoo Finance). Outbound HTTP queries are wrapped with Tenacity retries
                and cached in sector-dedicated DuckDB stores.
              </p>
              <ul className="mt-6 space-y-2.5 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>Direct endpoints for RBI Form A, Key Rates & FSR tables</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>DuckDB local columnar storage for zero latency queries</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>Strict cryptographic provenance hash on every fetched cell</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 10 Sector Agents Showcase */}
      <section id="sectors" className="py-24 border-t border-white/[0.08] bg-[#050b1a]/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-14">
            <div>
              <p className="mesh-eyebrow text-cyan-400 mb-3">_03/ Domain specialization_</p>
              <h2 className="mesh-section-title font-extrabold text-white">
                The 10 Macroeconomic Sector Agents
              </h2>
              <p className="mt-3 text-slate-400 text-sm max-w-xl">
                Every indicator has exactly one owner agent. The Finance and External Sectors are fully live with RBI DBIE, IMF SDMX, and DuckDB stores.
              </p>
            </div>

            <div className="mt-4 md:mt-0 flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-slate-200 font-semibold">Live Connected</span>
              </span>
              <span className="flex items-center gap-1.5 ml-4">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                <span className="text-slate-300">Staged</span>
              </span>
              <span className="flex items-center gap-1.5 ml-4">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-600" />
                <span className="text-slate-400">In Roadmap</span>
              </span>
            </div>
          </div>

          <div className="cv-auto grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {SECTOR_AGENTS.map((agent) => {
              const isLive = agent.status === 'active';
              const isStaged = agent.status === 'staged';

              return (
                <TiltCard key={agent.id} label={`${agent.name} sector`} maxTilt={5}>
                <div
                  className={`reveal-gsap p-6 rounded-3xl mesh-card relative border transition-all h-full ${
                    isLive
                      ? 'border-emerald-500/40 bg-emerald-950/10 hover:border-emerald-400 shadow-glow-emerald/20'
                      : isStaged
                      ? 'border-cyan-500/30 bg-cyan-950/5 hover:border-cyan-400'
                      : 'border-white/5 opacity-70 hover:opacity-95'
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className="w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-sm shadow-md"
                      style={{ backgroundColor: `${agent.color}20`, color: agent.color, border: `1px solid ${agent.color}40` }}
                    >
                      {agent.name.slice(0, 2).toUpperCase()}
                    </div>
                    <span
                      className={`text-[10px] font-mono uppercase px-2.5 py-1 rounded-full font-bold tracking-wider ${
                        isLive
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : isStaged
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {isLive ? '● Live Connected' : isStaged ? '○ Staged' : 'Planned'}
                    </span>
                  </div>

                  <h4 className="font-bold text-white text-lg tracking-tight">
                    {agent.name}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{agent.domain}</p>

                  <div className="mt-5 pt-3.5 border-t border-white/5 space-y-2">
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span className="text-slate-500">Data Source:</span>
                      <span className="font-medium text-slate-300 truncate max-w-[190px]">{agent.authority}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span className="text-slate-500">Indicators:</span>
                      <span className="font-medium text-slate-300 truncate max-w-[190px]">
                        {agent.ownership.slice(0, 2).join(', ')}
                      </span>
                    </div>
                  </div>

                  {isLive && (
                    <button
                      onClick={isAuthenticated ? onEnterWorkspace : onOpenAuth}
                      className="mt-5 w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 hover:from-emerald-500/30 hover:to-cyan-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold transition-all flex items-center justify-center gap-2 group"
                    >
                      <span>Analyze Sector Live</span>
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                    </button>
                  )}
                </div>
                </TiltCard>
              );
            })}
          </div>
        </div>
      </section>

      {/* Researcher stories — UI only, same actions */}
      <section aria-label="Researcher stories" className="reveal py-16 sm:py-24 border-t border-white/[0.08] relative bg-[#050b1a]/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <p className="mesh-eyebrow text-cyan-400 mb-3">_Researcher stories_</p>
            <h2 className="mesh-section-title font-extrabold text-white">Teams writing cited macro research</h2>
            <p className="mt-4 text-slate-400 text-sm sm:text-base">How policy, risk, and investment workflows change with a cited mesh.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-4 sm:gap-6">
            <figure className="mesh-quote rounded-3xl p-6 sm:p-7 flex flex-col">
              <blockquote className="text-sm text-slate-200 leading-relaxed flex-1">“We needed to move fast while staying compliant. With cited RBI telemetry, we can scale research responsibly.”</blockquote>
              <figcaption className="mt-5 pt-4 border-t border-white/10 flex items-center gap-3">
                <span className="w-9 h-9 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-xs font-bold text-brand-300">PR</span>
                <span><span className="block text-xs font-semibold text-white">Policy Research Desk</span><span className="block text-[11px] text-slate-500 font-mono">Transmission notes</span></span>
              </figcaption>
              <p className="mt-3 text-2xl font-extrabold text-white font-mono">2–4M <span className="text-xs font-mono font-medium text-slate-400">lag-mapped transmission</span></p>
            </figure>
            <figure className="mesh-quote rounded-3xl p-6 sm:p-7 flex flex-col">
              <blockquote className="text-sm text-slate-200 leading-relaxed flex-1">“The mesh went beyond data. Attribution on every figure became our model for review across the bank.”</blockquote>
              <figcaption className="mt-5 pt-4 border-t border-white/10 flex items-center gap-3">
                <span className="w-9 h-9 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-xs font-bold text-emerald-300">RK</span>
                <span><span className="block text-xs font-semibold text-white">Risk &amp; Solvency Team</span><span className="block text-[11px] text-slate-500 font-mono">NPA / CRAR watch</span></span>
              </figcaption>
              <p className="mt-3 text-2xl font-extrabold text-white font-mono">530bps <span className="text-xs font-mono font-medium text-slate-400">CRAR buffer surfaced</span></p>
            </figure>
            <figure className="mesh-quote rounded-3xl p-6 sm:p-7 flex flex-col">
              <blockquote className="text-sm text-slate-200 leading-relaxed flex-1">“We can scale without limits. Our research is faster, cited, and ready for whatever comes next.”</blockquote>
              <figcaption className="mt-5 pt-4 border-t border-white/10 flex items-center gap-3">
                <span className="w-9 h-9 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-xs font-bold text-cyan-300">AM</span>
                <span><span className="block text-xs font-semibold text-white">Asset Markets Desk</span><span className="block text-[11px] text-slate-500 font-mono">Credit &amp; rates</span></span>
              </figcaption>
              <p className="mt-3 text-2xl font-extrabold text-white font-mono">13.2M <span className="text-xs font-mono font-medium text-slate-400">months import cover checked</span></p>
            </figure>
          </div>
        </div>
      </section>

      {/* Platform stats band — UI only */}
      <section aria-label="Platform at a glance" className="reveal border-t border-white/[0.08] bg-gradient-to-r from-brand-600/[0.08] via-cyan-500/[0.06] to-purple-600/[0.08]">
        <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 text-center">
          <div><p className="mesh-eyebrow text-slate-500">_Agents_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">10</div></div>
          <div><p className="mesh-eyebrow text-slate-500">_DBIE tables_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">340+</div></div>
          <div><p className="mesh-eyebrow text-slate-500">_Cited answers_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">100%</div></div>
          <div><p className="mesh-eyebrow text-slate-500">_Provenance_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">99.9%</div></div>
          <div><p className="mesh-eyebrow text-slate-500">_Protocols_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">A2A+MCP</div></div>
          <div><p className="mesh-eyebrow text-slate-500">_Cache_</p><div className="text-3xl font-extrabold text-white font-mono mt-1">DuckDB</div></div>
        </div>
      </section>

      {/* Non-Negotiable Anti-Hallucination Policy */}
      <section id="governance" className="reveal py-16 sm:py-24 border-t border-white/[0.08] relative">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-cyan-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto mb-6 shadow-glow-emerald">
            <ShieldCheck className="w-8 h-8 text-emerald-400" />
          </div>
          <p className="mesh-eyebrow text-emerald-400 mb-3">_Institutional trust &amp; verification_</p>
          <h2 className="mesh-section-title font-extrabold text-white">
            &quot;No Source, No Answer&quot; Standard
          </h2>
          <p className="mt-4 text-slate-300 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            Financial decision-making demands absolute integrity. In Macrograph-AI, agents are strictly prohibited from generating, guessing, or hardcoding unverified numbers.
          </p>

          {/* Provenance strip — static authority pills, UI only */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-2" aria-label="Provenance coverage">
            {['RBI DBIE mirrors', 'MoSPI releases', 'IMF SDMX 3.0', 'NSE market feeds', 'DuckDB cache'].map((p) => (
              <span key={p} className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[11px] font-mono text-emerald-200 bg-emerald-500/10 border border-emerald-500/25">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                {p}
              </span>
            ))}
          </div>

          <div className="mt-12 grid sm:grid-cols-3 gap-6 text-left">
            <div className="p-6 rounded-2xl mesh-card border border-white/5 space-y-2">
              <div className="text-cyan-400 font-bold text-sm font-mono flex items-center gap-2">
                <span>01. Strict Attribution</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Every claim must state the <strong>source agent</strong>, the <strong>FastMCP tool</strong>, official table reference, and observation period.
              </p>
            </div>
            <div className="p-6 rounded-2xl mesh-card border border-white/5 space-y-2">
              <div className="text-cyan-400 font-bold text-sm font-mono flex items-center gap-2">
                <span>02. Structured Fallbacks</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                If data is unverified or unavailable, the agent explicitly emits <code className="text-rose-400 font-mono">status: unavailable</code> rather than fabricating values.
              </p>
            </div>
            <div className="p-6 rounded-2xl mesh-card border border-white/5 space-y-2">
              <div className="text-cyan-400 font-bold text-sm font-mono flex items-center gap-2">
                <span>03. Dual Verification</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Seamlessly bridges canonical government data (RBI DBIE, MoSPI, IMF) with real-time financial market spot rates (Yahoo Finance) and breaking news (Tavily).
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Closing call-to-action — UI only, same actions */}
      <section aria-label="Get started" className="reveal mesh-cta-band border-t border-white/[0.08]">
        <div className="max-w-5xl mx-auto px-6 py-16 sm:py-20 text-center">
          <p className="mesh-eyebrow text-cyan-300 mb-3">_Citations on every figure_</p>
          <h2 className="mesh-section-title font-extrabold text-white">Bring every sector into one view</h2>
          <p className="mt-4 text-slate-300 text-sm sm:text-base max-w-2xl mx-auto">Turn scattered releases into one cited research workspace.</p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={isAuthenticated ? onEnterWorkspace : onOpenAuth}
              className="touch-44 w-full sm:w-auto py-4 px-9 rounded-2xl bg-gradient-to-r from-brand-500 via-indigo-600 to-cyan-500 hover:from-brand-400 hover:to-cyan-400 text-white font-bold text-base shadow-glow-brand transition-all flex items-center justify-center gap-3 group"
            >
              <span>{isAuthenticated ? 'Open Research Workspace' : 'Explore the Platform'}</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" aria-hidden="true" />
            </button>
            <a href="#console" className="touch-44 w-full sm:w-auto py-4 px-8 rounded-2xl glass-panel text-slate-200 font-semibold text-sm transition-all flex items-center justify-center gap-2.5 border border-white/10 hover:border-cyan-400/40">
              <Terminal className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              <span>See it in action</span>
            </a>
          </div>
        </div>
      </section>

      {/* Site footer — UI only */}
      <footer className="border-t border-white/10 pt-14 pb-10 bg-[#030612] text-slate-400 text-xs">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10 text-left">
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Platform</h4>
              <ul className="space-y-2.5">
                <li><a href="#console" className="hover:text-cyan-300 transition-colors">Architecture Console</a></li>
                <li><a href="#protocols" className="hover:text-cyan-300 transition-colors">Dual-Protocol Mesh</a></li>
                <li><a href="#sectors" className="hover:text-cyan-300 transition-colors">Sector Agents</a></li>
                <li><a href="#governance" className="hover:text-cyan-300 transition-colors">Citation Guarantee</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Data Authorities</h4>
              <ul className="space-y-2.5">
                <li><span>RBI DBIE Official Mirrors</span></li>
                <li><span>MoSPI National Accounts</span></li>
                <li><span>IMF SDMX 3.0 BPM6</span></li>
                <li><span>NSE Market Feeds</span></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Protocols</h4>
              <ul className="space-y-2.5">
                <li><span>A2A Reasoning Layer</span></li>
                <li><span>FastMCP Data Gateways</span></li>
                <li><span>DuckDB Sector Stores</span></li>
                <li><span>NetworkX Causal Graph</span></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Trust</h4>
              <ul className="space-y-2.5">
                <li className="flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> No Source, No Answer</li>
                <li><span>Strict Attribution Chain</span></li>
                <li><span>Structured Fallbacks</span></li>
              </ul>
            </div>
          </div>
          <div className="pt-6 border-t border-white/10 flex flex-col lg:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
                <Network className="w-4 h-4 text-brand-400" />
              </div>
              <span className="text-slate-200 font-bold text-sm">Macrograph-AI</span>
              <span className="text-slate-600">|</span>
              <span>Indian Macroeconomic Multi-Agent Intelligence Mesh</span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-slate-400 font-mono text-[11px]">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-300">
                <span className="mesh-status-dot w-1.5 h-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
                <span>All sector mirrors operational</span>
              </span>
              <span>FastAPI</span><span aria-hidden="true">•</span><span>FastMCP</span><span aria-hidden="true">•</span><span>LangGraph A2A</span><span aria-hidden="true">•</span><span>DuckDB</span><span aria-hidden="true">•</span><span>Groq Llama-3.3</span>
            </div>
          </div>
          <div className="mt-6 pt-5 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-500">
            <span>© 2026 Macrograph-AI • Cited macro research workspace</span>
            <span className="font-mono">Privacy • Terms • Status: operational</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
