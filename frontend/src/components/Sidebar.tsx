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
  ChevronRight
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

  return (
    <aside className="w-72 h-screen flex flex-col bg-slate-950/90 border-r border-white/5 backdrop-blur-xl shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-400 p-[1px] shadow-glow-brand">
            <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Network className="w-4 h-4 text-brand-400" />
            </div>
          </div>
          <div>
            <div className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
              <span>Macrograph</span>
              <span className="text-brand-400 text-xs px-1.5 py-0.2 rounded bg-brand-500/10 border border-brand-500/20">AI</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono">Indian Macro Intelligence</div>
          </div>
        </div>
      </div>

      {/* Main Navigation Views */}
      <div className="p-3 border-b border-white/5 space-y-1">
        <button
          onClick={() => onSelectView('dashboard')}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            currentView === 'dashboard'
              ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <BarChart3 className="w-4 h-4 text-brand-400" />
          <span>Dashboard & Visuals</span>
        </button>

        <button
          onClick={() => onSelectView('chat')}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            currentView === 'chat'
              ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <MessageSquare className="w-4 h-4 text-emerald-400" />
          <span>Agent Chat Workspace</span>
        </button>

        <button
          onClick={() => onSelectView('knowledge_graph')}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            currentView === 'knowledge_graph'
              ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Share2 className="w-4 h-4 text-cyan-400" />
          <span>Causal Transmission Graph</span>
        </button>

        <button
          onClick={() => onSelectView('a2a_registry')}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            currentView === 'a2a_registry'
              ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <BookOpen className="w-4 h-4 text-indigo-400" />
          <span>A2A Agent Registry</span>
        </button>
      </div>

      {/* Agents List Header */}
      <div className="px-4 pt-4 pb-2 flex items-center justify-between">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-brand-400" />
          <span>Macro Agents</span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          {activeAgentCount} Active
        </span>
      </div>

      {/* Agents Scrollable List */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1.5">
        {SECTOR_AGENTS.map((agent) => {
          const isSelected = selectedAgentId === agent.id;
          const isOrchestrator = agent.id === 'orchestrator';
          const isFinance = agent.id === 'finance_sector';
          const isAdditionalSector = [
            'external_sector',
            'capital_market_sector',
            'labour_sector',
            'monetary_sector',
          ].includes(agent.id);
          const isSelectable = agent.status === 'active';

          return (
            <div
              key={agent.id}
              onClick={() => {
                if (isSelectable) {
                  onSelectAgent(agent.id);
                  onSelectView('chat');
                }
              }}
              className={`p-2.5 rounded-xl transition-all relative group ${
                isSelectable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
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
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 truncate">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold font-mono"
                    style={{
                      backgroundColor: `${agent.color}20`,
                      color: agent.color,
                      border: `1px solid ${agent.color}40`,
                    }}
                  >
                    {isOrchestrator ? 'OR' : isFinance ? 'FN' : agent.name.slice(0, 2).toUpperCase()}
                  </div>

                  <div className="truncate">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-medium truncate ${isSelected ? 'text-white font-semibold' : 'text-slate-300'}`}>
                        {agent.name}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate">
                      {isOrchestrator
                        ? 'Multi-agent router'
                        : isFinance
                        ? 'Live RBI DBIE connected'
                        : agent.authority}
                    </div>
                  </div>
                </div>

                {isSelectable ? (
                  <div className="flex items-center gap-1">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isFinance
                          ? 'bg-emerald-400 animate-pulse'
                          : isAdditionalSector
                          ? 'bg-emerald-400'
                          : isOrchestrator
                          ? 'bg-brand-400'
                          : ''
                      }`}
                      style={{
                        backgroundColor:
                          isOrchestrator || isFinance || isAdditionalSector || !isSelectable
                            ? undefined
                            : agent.color,
                      }}
                    />
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 transition-colors" />
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                    <Lock className="w-3 h-3 text-slate-600" />
                    <span>Soon</span>
                  </div>
                )}
              </div>

              {isFinance && (
                <div className="mt-1.5 flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Real RBI DBIE Data Active</span>
                </div>
              )}
              {isAdditionalSector && (
                <div className="mt-1.5 flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Direct Sector Agent • Source freshness per response</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* User Profile Footer */}
      <div className="p-3 border-t border-white/5 bg-slate-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 truncate">
            <img
              src={user.avatar}
              alt={user.name}
              className="w-8 h-8 rounded-full object-cover border border-white/10"
            />
            <div className="truncate">
              <div className="text-xs font-medium text-white truncate">{user.name}</div>
              <div className="text-[10px] text-slate-400 truncate">{user.role}</div>
            </div>
          </div>
          <button
            onClick={onLogout}
            title="Sign Out"
            className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-white/5 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
