import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface NavbarProps {
  onOpenSignIn: () => void;
  onOpenAgents: () => void;
  onOpenDemo: () => void;
  onOpenResearch: () => void;
  user: string | null;
  systemStatus: {
    online: boolean;
    agentsCount: number;
    nodesCount: number;
  };
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenSignIn,
  onOpenAgents,
  onOpenDemo,
  onOpenResearch,
  user,
  systemStatus,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleNavClick = (callback?: () => void) => {
    setMobileMenuOpen(false);
    if (callback) callback();
  };

  return (
    <header className="relative w-full pt-3 sm:pt-4 pb-2 px-4 sm:px-12 md:px-16 z-30 transition-all duration-200">
      <div className="flex items-center justify-between">
        {/* Brand Logo */}
        <div 
          onClick={() => handleNavClick(() => window.scrollTo({ top: 0, behavior: 'smooth' }))}
          className="flex items-center gap-2.5 sm:gap-3 cursor-pointer group"
        >
          <div className="relative w-7 h-7 sm:w-8 sm:h-8 transition-transform duration-300 group-hover:scale-105">
            <svg viewBox="0 0 40 40" className="w-full h-full drop-shadow-sm">
              <defs>
                <linearGradient id="navFacet1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="100%" stopColor="#0f172a" />
                </linearGradient>
                <linearGradient id="navFacet2" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#0284c7" />
                </linearGradient>
                <linearGradient id="navFacet3" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0ea5e9" />
                  <stop offset="100%" stopColor="#0369a1" />
                </linearGradient>
              </defs>
              <polygon points="20,4 34,12 20,20 6,12" fill="url(#navFacet2)" />
              <polygon points="6,12 20,20 20,36 6,28" fill="url(#navFacet1)" />
              <polygon points="20,20 34,12 34,28 20,36" fill="url(#navFacet3)" />
              <line x1="20" y1="20" x2="20" y2="36" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="20" y1="20" x2="6" y2="12" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="20" y1="20" x2="34" y2="12" stroke="#0f172a" strokeWidth="1.5" />
            </svg>
          </div>
          <span className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 drop-shadow-sm font-sans">
            MacroGraph AI
          </span>
        </div>

        {/* Center Nav Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-7 lg:gap-8 text-[14px] lg:text-[15px] font-medium text-slate-800">
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="text-slate-950 font-semibold hover:text-black transition-colors focus:outline-none"
          >
            Home
          </button>
          <button
            onClick={onOpenDemo}
            className="text-slate-700 hover:text-slate-950 transition-colors focus:outline-none"
          >
            Explore
          </button>
          <button
            onClick={onOpenAgents}
            className="text-slate-700 hover:text-slate-950 transition-colors focus:outline-none"
          >
            Agents
          </button>
          <button
            onClick={onOpenAgents}
            className="text-slate-700 hover:text-slate-950 transition-colors focus:outline-none"
          >
            Sectors
          </button>
          <button
            onClick={onOpenResearch}
            className="text-slate-700 hover:text-slate-950 transition-colors focus:outline-none"
          >
            Insights
          </button>
        </nav>

        {/* Right Controls: Backend Status Badge & Sign In Button */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Backend Connectivity Badge (Hidden on very small screens) */}
          <div 
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/70 backdrop-blur-sm border border-slate-200/80 text-[11px] font-medium text-slate-700 shadow-xs"
            title={systemStatus.online ? `Connected: ${systemStatus.agentsCount} Active Sector Agents, ${systemStatus.nodesCount} Causal Nodes` : 'Connecting to local Macrograph AI engine...'}
          >
            <span className={`w-2 h-2 rounded-full ${systemStatus.online ? 'bg-emerald-500 pulse-indicator' : 'bg-amber-400 animate-pulse'}`} />
            <span>{systemStatus.online ? `${systemStatus.agentsCount} Agents Live` : 'Connecting'}</span>
          </div>

          {/* Sign In Button / Active User Badge */}
          {user ? (
            <div className="flex items-center gap-1.5 bg-[#0b1320] text-white text-xs font-semibold px-3 py-1.5 rounded-xl shadow-sm border border-cyan-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="max-w-[100px] sm:max-w-[140px] truncate">{user}</span>
            </div>
          ) : (
            <button
              onClick={onOpenSignIn}
              className="bg-[#0b1320] hover:bg-slate-800 text-white text-xs sm:text-[14px] font-semibold px-4 sm:px-6 py-2 rounded-xl transition-all duration-200 shadow-md hover:shadow-lg active:scale-95"
            >
              Sign in
            </button>
          )}

          {/* Mobile Hamburger Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl bg-white/70 backdrop-blur-sm border border-slate-200/80 text-slate-800 hover:text-black hover:bg-white transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Slide-down Navigation Panel */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-3 p-4 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 text-white shadow-2xl space-y-3 animate-fade-in z-50">
          <div className="flex flex-col space-y-2 text-sm font-medium">
            <button
              onClick={() => handleNavClick(() => window.scrollTo({ top: 0, behavior: 'smooth' }))}
              className="text-left py-2 px-3 rounded-lg hover:bg-slate-800 text-white font-semibold transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => handleNavClick(onOpenDemo)}
              className="text-left py-2 px-3 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors"
            >
              Explore Scenarios
            </button>
            <button
              onClick={() => handleNavClick(onOpenAgents)}
              className="text-left py-2 px-3 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors"
            >
              Domain Agents (8 Sectors)
            </button>
            <button
              onClick={() => handleNavClick(onOpenAgents)}
              className="text-left py-2 px-3 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors"
            >
              Economic Sectors
            </button>
            <button
              onClick={() => handleNavClick(onOpenResearch)}
              className="text-left py-2 px-3 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors"
            >
              Macro Insights & Research
            </button>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${systemStatus.online ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span>{systemStatus.agentsCount} Domain Agents Active</span>
            </div>
            <span className="font-mono text-cyan-400">{systemStatus.nodesCount} KG Nodes</span>
          </div>
        </div>
      )}
    </header>
  );
};

