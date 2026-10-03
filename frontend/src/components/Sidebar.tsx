import React, { useState } from 'react';
import {
  Network,
  BarChart3,
  MessageSquare,
  Share2,
  BookOpen,
  LogOut,
  Lock,
  CheckCircle2,
  Layers,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  X,
} from 'lucide-react';
import { SECTOR_AGENTS } from '../data/agents';
import { UserProfile } from '../types';

interface SidebarProps {
  currentView: 'dashboard' | 'chat' | 'knowledge_graph' | 'a2a_registry';
  onSelectView: (view: 'dashboard' | 'chat' | 'knowledge_graph' | 'a2a_registry') => void;
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  user: UserProfile;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  selectedAgentId,
  onSelectAgent,
  user,
  onLogout,
}) => {
  const activeAgentCount = SECTOR_AGENTS.filter((agent) => agent.status === 'active').length;
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSelectView = (view: SidebarProps['currentView']) => {
    onSelectView(view);
    setMobileOpen(false);
  };

  const handleSelectAgent = (agentId: string) => {
    onSelectAgent(agentId);
    onSelectView('chat');
    setMobileOpen(false);
  };

  const sidebarBody = (isMobile: boolean) => (
    <div className="flex flex-col h-full">
      {/* Brand Header */}
      <div className="p-4 border-b border-white/[0.08] flex items-center justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 via-cyan-500 to-indigo-500 p-[1px] shadow-glow-brand shrink-0">
            <div className="w-full h-full bg-[#060b18] rounded-[11px] flex items-center justify-center">
              <Network className="w-4 h-4 text-brand-400" />
            </div>
          </div>
          {(!collapsed || isMobile) && (
            <div className="min-w-0">
              <div className="font-extrabold text-sm tracking-tight text-white flex items-center gap-1.5">
                <span className="truncate">Macrograph</span>
                <span className="text-cyan-300 text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 shrink-0">AI MESH</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono tracking-tight flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                <span className="truncate">Multi-Agent Architecture</span>
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {!isMobile && (
            <button
              onClick={() => setCollapsed((v) => !v)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={collapsed ? 'Expand' : 'Collapse'}
              className="touch-44 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors flex items-center justify-center"
            >
              {collapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </button>
          )}
          {isMobile && (
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
              className="touch-44 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors flex items-center justify-center"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
      {/* Main Navigation Views */}
      <nav aria-label="Workspace views" className="p-3 border-b border-white/[0.08] space-y-1.5">
        {[
          { id: 'dashboard' as const, label: collapsed && !isMobile ? 'Dashboard' : 'Dashboard & Telemetry', icon: <BarChart3 className="w-4 h-4 text-cyan-400 shrink-0" /> },
          { id: 'chat' as const, label: collapsed && !isMobile ? 'Workspace' : 'Agent Research Workspace', icon: <MessageSquare className="w-4 h-4 text-emerald-400 shrink-0" /> },
          { id: 'knowledge_graph' as const, label: collapsed && !isMobile ? 'Graph' : 'Causal Transmission Graph', icon: <Share2 className="w-4 h-4 text-cyan-400 shrink-0" /> },
          { id: 'a2a_registry' as const, label: collapsed && !isMobile ? 'Registry' : 'A2A Agent Registry', icon: <BookOpen className="w-4 h-4 text-indigo-400 shrink-0" /> },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => handleSelectView(item.id)}
            aria-current={currentView === item.id ? 'page' : undefined}
            title={item.label}
            className={`touch-44 w-full flex items-center gap-3 px-3.5 rounded-xl text-xs font-semibold transition-all ${
              currentView === item.id
                ? 'bg-gradient-to-r from-brand-600/30 to-cyan-600/20 text-cyan-200 border border-cyan-500/40 shadow-glow-cyan/20'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04] border border-transparent'
            } ${collapsed && !isMobile ? 'justify-center py-3' : 'py-2.5'}`}
          >
            {item.icon}
            {(!collapsed || isMobile) && <span className="truncate">{item.label}</span>}
          </button>
        ))}
      </nav>

      {/* Agents List Header */}
      {(!collapsed || isMobile) && (
        <div className="px-4 pt-4 pb-2 flex items-center justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-brand-400" />
            <span>Macro Agents</span>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {activeAgentCount} Active
          </span>
        </div>
      )}

      {/* Agents Scrollable List */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1.5" role="list" aria-label="Macro agents">
        {SECTOR_AGENTS.map((agent) => {
          const isSelected = selectedAgentId === agent.id;
          const isOrchestrator = agent.id === 'orchestrator';
          const isFinance = agent.id === 'finance_sector';
          const isAdditionalSector = [
            'external_sector',
            'capital_market_sector',
            'labour_sector',
            'monetary_sector',
            'real_sector',
          ].includes(agent.id);
          const isSelectable = agent.status === 'active';

          if (collapsed && !isMobile) {
            return (
              <button
                key={agent.id}
                role="listitem"
                disabled={!isSelectable}
                onClick={() => { if (isSelectable) handleSelectAgent(agent.id); }}
                title={`${agent.name}${isSelectable ? '' : ' — coming soon'}`}
                aria-label={`${agent.name}${isSelected ? ' (selected)' : ''}`}
                aria-current={isSelected ? 'true' : undefined}
                className={`touch-44 w-full p-2 rounded-xl transition-all flex items-center justify-center ${
                  isSelected
                    ? 'bg-slate-800/90 border border-brand-500/50'
                    : isSelectable
                    ? 'bg-slate-900/40 hover:bg-slate-800/60 border border-white/5'
                    : 'bg-slate-950/40 border border-transparent opacity-50 cursor-not-allowed'
                }`}
              >
                <span
                  className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold font-mono"
                  style={{ backgroundColor: `${agent.color}20`, color: agent.color, border: `1px solid ${agent.color}40` }}
                >
                  {isOrchestrator ? 'OR' : isFinance ? 'FN' : agent.name.slice(0, 2).toUpperCase()}
                </span>
              </button>
            );
          }

          return (
            <button
              key={agent.id}
              role="listitem"
              disabled={!isSelectable}
              onClick={() => { if (isSelectable) handleSelectAgent(agent.id); }}
              aria-label={`${agent.name}${isSelected ? ' (selected)' : ''}${isSelectable ? '' : ' — coming soon'}`}
              className={`touch-44 w-full p-2.5 rounded-xl transition-all relative group text-left ${
                isSelectable ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
              } ${
                isSelected
                  ? isAdditionalSector
                    ? 'bg-slate-800/90 border border-emerald-500/50 shadow-glow-emerald/20'
                    : 'bg-slate-800/90 border border-brand-500/50 shadow-glow-brand/20'
                  : isSelectable
                  ? 'bg-slate-900/40 hover:bg-slate-800/60 border border-white/5 hover:border-white/10'
                  : 'bg-slate-950/40 border border-transparent'
              }`}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2.5 truncate">
                  <span
                    className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold font-mono"
                    style={{ backgroundColor: `${agent.color}20`, color: agent.color, border: `1px solid ${agent.color}40` }}
                  >
                    {isOrchestrator ? 'OR' : isFinance ? 'FN' : agent.name.slice(0, 2).toUpperCase()}
                  </span>
                  <span className="truncate">
                    <span className={`text-xs font-medium truncate block ${isSelected ? 'text-white font-semibold' : 'text-slate-300'}`}>
                      {agent.name}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate block">
                      {isOrchestrator ? 'Multi-agent router' : isFinance ? 'Live RBI DBIE connected' : agent.authority}
                    </span>
                  </span>
                </span>
                {isSelectable ? (
                  <span className="flex items-center gap-1 shrink-0">
                    <span
                      className={`w-2 h-2 rounded-full ${isFinance ? 'bg-emerald-400 animate-pulse' : isAdditionalSector ? 'bg-emerald-400' : isOrchestrator ? 'bg-brand-400' : ''}`}
                      style={{ backgroundColor: isOrchestrator || isFinance || isAdditionalSector || !isSelectable ? undefined : agent.color }}
                    />
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 transition-colors" />
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[10px] text-slate-500 font-mono shrink-0">
                    <Lock className="w-3 h-3 text-slate-600" />
                    <span>Soon</span>
                  </span>
                )}
              </span>
              {isFinance && (!collapsed || isMobile) && (
                <span className="mt-1.5 flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Real RBI DBIE Data Active</span>
                </span>
              )}
              {isAdditionalSector && (!collapsed || isMobile) && (
                <span className="mt-1.5 flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Direct Sector Agent • Source freshness per response</span>
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* User Profile Footer */}
      <div className="p-3 border-t border-white/5 bg-slate-900/50">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 truncate min-w-0">
            <img src={user.avatar} alt={user.name} loading="lazy" className="w-8 h-8 rounded-full object-cover border border-white/10 shrink-0" />
            {(!collapsed || isMobile) && (
              <div className="truncate min-w-0">
                <div className="text-xs font-medium text-white truncate">{user.name}</div>
                <div className="text-[10px] text-slate-400 truncate">{user.role}</div>
              </div>
            )}
          </div>
          <button
            onClick={onLogout}
            title="Sign Out"
            aria-label="Sign out"
            className="touch-44 p-2.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-white/5 transition-colors flex items-center justify-center shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — collapsible, UI only */}
      <aside aria-label="Workspace navigation" className={`${collapsed ? 'w-[76px]' : 'w-72'} hidden md:flex h-screen flex-col bg-[#050a18] border-r border-white/[0.08] backdrop-blur-2xl shrink-0 select-none transition-all duration-300`}>
        {sidebarBody(false)}
      </aside>

      {/* Mobile top bar trigger — UI only, same callbacks */}
      <button
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation menu"
        className="md:hidden fixed bottom-5 left-5 z-40 touch-44 w-12 h-12 rounded-2xl bg-gradient-to-r from-brand-600 to-cyan-600 text-white shadow-glow-brand flex items-center justify-center"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile drawer — UI only */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Workspace navigation">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-[300px] max-w-[85vw] bg-[#050a18] border-r border-white/10 flex flex-col">
            {sidebarBody(true)}
          </aside>
        </div>
      )}
    </>
  );
};
