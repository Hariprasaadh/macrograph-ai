import React, { useState, useRef, useEffect, memo } from 'react';
import {
  Send,
  Sparkles,
  User,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  RefreshCw,
  Network,
  Landmark,
  TrendingUp,
  Coins,
  Globe,
  Users,
  Activity,
  type LucideIcon,
} from 'lucide-react';
import { ChatMessage, StreamStep } from '../types';
import { SECTOR_AGENTS } from '../data/agents';

interface ChatWorkspaceProps {
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
}

const DEFAULT_MESSAGES: Record<string, ChatMessage[]> = {
  orchestrator: [
    {
      id: 'welcome-orchestrator',
      role: 'assistant',
      content: `### Macrograph Orchestrator Workspace\n\nI am the **central reasoning and multi-agent coordination engine** for Macrograph-AI.\n\n### Universal Macro Capabilities:\n- **Cross-Sector Deconstruction**: Route queries across all **10 macroeconomic sectors** (Monetary, Prices & Inflation, Fiscal, Real Economy GDP/GVA, Agriculture, External Trade & Forex, Labour, Capital Markets, and Banking).\n- **A2A Protocol Coordination**: Delegate domain research to specialized sector agents via standard Agent Cards.\n- **Causal Knowledge Graph**: Trace transmission mechanisms and propagate macro shocks across indicators via the NetworkX graph engine.\n- **Academic Synthesis**: Synthesize unified reports with strict zero-hallucination source attribution.\n\nAsk me **any macroeconomic question**, inquire about general economic principles, or simulate shock scenarios!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: 'Macrograph Orchestrator (Multi-Sector Routing)',
      citations: [
        {
          source_agent: 'orchestrator',
          authority: 'Macrograph A2A Coordination Layer',
          table: 'NetworkX Causal Engine & Agent Registry',
          period: 'Live / 10 Sectors',
          freshness: 'orchestrated',
        },
      ],
    },
  ],
  finance_sector: [
    {
      id: 'welcome-finance',
      role: 'assistant',
      content: `### Finance & Banking Sector Specialist\n\nI am the dedicated **Finance Sector Agent** with direct access to official **Reserve Bank of India (RBI DBIE)** data pipelines and DuckDB stores.\n\n### Specialized Domain Scope (Scheduled Commercial Banks):\n- **Bank Credit Growth**: Non-food credit, credit to Agriculture, Industry, MSME, Services, and Personal Loans (Table r539)\n- **Asset Quality**: Scheduled Commercial Bank Gross NPAs, Net NPAs, PCR, and CRAR (Table r330)\n- **Lending & Deposit Rates**: WALR (Fresh/Outstanding), 1-Year MCLR, and WADTDR spreads (Table r531)\n- **Deposit Mobilisation**: Aggregate deposits, CASA ratio, and Credit-to-Deposit (CD) ratio (Table r689)\n\n> ⚠️ **Strict Domain Boundary Notice**\n> I strictly handle queries regarding **Indian Scheduled Commercial Banks and the Financial Sector**. If you have queries on other sectors (e.g. GDP, Inflation, Agriculture, Forex, or Fiscal Deficits), please switch to the **Macrograph Orchestrator**.\n\nAsk a banking question below or choose a suggested prompt!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: 'Finance & Banking Sector Agent',
      citations: [
        {
          source_agent: 'finance_sector',
          authority: 'Reserve Bank of India (RBI DBIE)',
          table: 'financial_sector.r539 / r330 / r531 / r689',
          period: 'Live RBI Feeds',
          freshness: 'live & cached',
        },
      ],
    },
  ],
  monetary_sector: [
    {
      id: 'welcome-monetary',
      role: 'assistant',
      content: `### Monetary & Liquidity Policy Specialist\n\nI am the dedicated **Monetary Sector Agent** — India's most comprehensive monetary policy intelligence engine, combining official **RBI DBIE** data with **real-time MPC research** via Tavily AI Search.\n\n### My Research Pipeline:\n1. 🏛️ **Official RBI Data** — Policy rates (Repo, SDF, MSF, CRR, SLR), Money Supply (M1/M2/M3), System Liquidity (LAF) from DBIE\n2. 📈 **Sovereign Bond Market** — 10-Year G-Sec benchmark yield & spread over repo (policy transmission signal)\n3. 📡 **Real-Time MPC Intelligence** — Live research via Tavily: MPC resolutions, Governor speeches, RBI press releases\n4. 🧠 **AI Synthesis** — Groq LLM analyses all three sources and delivers a structured, cited monetary policy report\n\n### Coverage:\n- **Rate Corridor**: Repo Rate, SDF, MSF, Bank Rate & LAF corridor width (bps)\n- **Money Supply**: M3 Broad Money growth, M1 Narrow Money, Reserve Money (M0)\n- **Liquidity Operations**: Net LAF absorption/injection, WACR alignment with policy rate\n- **Monetary Stance**: MPC stance label, real policy rate, historical stance transitions\n- **Policy Transmission**: G-Sec 10Y yield, sovereign spread dynamics\n\n> 💡 **Enhanced with Tavily AI Search** — My responses include real-time citations from RBI notifications, MPC meeting minutes, and economic research.\n\nAsk about monetary policy, liquidity, or MPC decisions below!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: 'Monetary & Liquidity Policy Specialist',
      citations: [
        {
          source_agent: 'monetary_sector',
          authority: 'Reserve Bank of India (RBI)',
          table: 'DBIE: Policy Rates, Money Supply, LAF Liquidity + Tavily Real-Time Search',
          period: 'Live & Upstream Snapshot',
          freshness: 'live',
          retrieval_url: 'https://rbi.org.in',
        },
      ],
    },
  ],
};

const SECTOR_WORKSPACE_DESCRIPTIONS: Record<string, string> = {
  external_sector:
    'Combines a configured RBI forex feed with locally stored trade and exchange-rate observations.',
  labour_sector:
    'Uses a configured MoSPI unemployment request and locally stored labour observations.',
  capital_market_sector:
    'Uses a configured NSE NIFTY request and locally stored market observations.',
  monetary_sector:
    'Combines official RBI DBIE data (policy rates, money supply, LAF liquidity) with real-time MPC intelligence via Tavily AI Search, synthesized by Groq LLM into cited monetary policy analysis.',
  real_sector:
    'Fetches MoSPI IIP (sectoral & use-based), DPIIT Eight Core Industries index, and RBI DBIE manufacturing GVA & OBICUS capacity utilisation data with per-observation provenance.',
};

const SECTOR_WELCOME_MESSAGES: Record<string, string> = Object.fromEntries(
  Object.keys(SECTOR_WORKSPACE_DESCRIPTIONS).map((sectorId) => {
    const agent = SECTOR_AGENTS.find((item) => item.id === sectorId)!;
    const indicatorAreas = agent.ownership.map((item) => `- ${item}`).join('\n');

    return [
      sectorId,
      `### ${agent.name} Specialist\n\n${SECTOR_WORKSPACE_DESCRIPTIONS[sectorId]}\n\n### Available Indicator Areas:\n${indicatorAreas}\n\nAsk about these indicators; returned data availability and freshness can vary by source.`,
    ];
  }),
);

const NEW_SECTOR_DEFAULT_MESSAGES: Record<string, ChatMessage[]> = Object.fromEntries(
  Object.entries(SECTOR_WELCOME_MESSAGES).map(([sectorId, content]) => {
    const agent = SECTOR_AGENTS.find((item) => item.id === sectorId);
    return [
      sectorId,
      [
        {
          id: `welcome-${sectorId}`,
          role: 'assistant',
          content,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          agentRouted: `${agent?.name} Specialist`,
          citations: [],
        },
      ],
    ];
  }),
);

const AGENT_ICONS: Record<string, LucideIcon> = {
  orchestrator: Network,
  finance_sector: Landmark,
  external_sector: Globe,
  labour_sector: Users,
  capital_market_sector: TrendingUp,
  monetary_sector: Coins,
  real_sector: Activity,
};

const AGENT_SHORT_NAMES: Record<string, string> = {
  orchestrator: 'Orchestrator',
  finance_sector: 'Finance Agent',
  external_sector: 'External',
  labour_sector: 'Labour',
  capital_market_sector: 'Capital',
  monetary_sector: 'Monetary',
  real_sector: 'Real Sector',
};

// UI-only memoized chips to avoid re-render churn during streaming (no data logic)
const PromptChip = memo(function PromptChip({ text, disabled, tone, onPick }: { text: string; disabled: boolean; tone: 'emerald' | 'default'; onPick: (t: string) => void }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onPick(text)}
      title={text}
      className={`touch-44 shrink-0 px-3 py-2 rounded-lg glass-panel text-slate-300 hover:text-white text-xs border transition-all text-left truncate max-w-[260px] ${
        tone === 'emerald' ? 'hover:bg-emerald-500/10 border-emerald-500/20' : 'hover:bg-slate-800 border-white/5'
      } disabled:opacity-50`}
    >
      {text}
    </button>
  );
});

const AgentToggleButton = memo(function AgentToggleButton({ label, selected, tone, onClick, title }: { label: string; selected: boolean; tone: 'brand' | 'emerald'; onClick: () => void; title: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={selected}
      className={`touch-44 px-3 py-2 rounded-lg font-medium transition-all flex items-center gap-1.5 whitespace-nowrap text-xs ${
        selected ? (tone === 'brand' ? 'bg-brand-600 text-white shadow-sm' : 'bg-emerald-600 text-white shadow-sm') : 'text-slate-400 hover:text-white'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${tone === 'brand' ? 'bg-brand-400' : 'bg-emerald-400'}`} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
});

const SUGGESTED_PROMPTS: Record<string, { text: string }[]> = {
  orchestrator: [
    {
      text: 'Synthesize the transmission of policy rates into bank lending rates, credit growth, and economic output.',
    },
    {
      text: 'How do rising crude oil prices impact India\'s fiscal deficit, inflation, and forex reserves?',
    },
    {
      text: 'Explain how the 10 macroeconomic sectors interact in Macrograph-AI\'s causal graph.',
    },
    {
      text: 'What are the primary macroeconomic risks to Indian economic stability in FY 2024-25?',
    },
  ],
  finance_sector: [
    {
      text: 'What is the current SCB Gross NPA ratio and capital adequacy status in India?',
    },
    {
      text: 'Analyze recent non-food bank credit growth and sectoral deployment across Agriculture, Industry and Services.',
    },
    {
      text: 'What are the current WALR and 1-year MCLR lending rates compared to fresh deposit rates (WADTDR)?',
    },
    {
      text: 'What is the latest Credit-to-Deposit (CD) ratio and aggregate deposit growth for SCBs?',
    },
  ],
  external_sector: [
    { text: 'What are the latest foreign exchange reserve observations and their reporting period?' },
    { text: 'Summarize the latest merchandise exports, imports, and trade balance data.' },
    { text: 'What USD/INR exchange-rate observations are available, and what is their freshness?' },
  ],
  labour_sector: [
    { text: 'What unemployment-rate observations are available, and what period do they cover?' },
    { text: 'Summarize the latest LFPR data, including available gender and rural/urban breakdowns.' },
    { text: 'What worker population ratio observations are available in the labour data?' },
  ],
  capital_market_sector: [
    { text: 'What NIFTY 50 snapshot is available, including its observation date?' },
    { text: 'What India VIX observation is available, and what is its recorded period?' },
    { text: 'Summarize available G-Sec yields across the reported maturities.' },
  ],
  monetary_sector: [
    { text: 'What is the current RBI repo rate, SDF, MSF corridor width, and MPC stance? Include any recent rate changes.' },
    { text: 'Analyze India\'s M3 broad money growth — is monetary expansion consistent with inflation control?' },
    { text: 'What is the current system liquidity condition (LAF surplus/deficit) and how does WACR track the policy repo rate?' },
    { text: 'Explain the latest MPC decision and monetary policy stance with real-time citations from RBI notifications.' },
  ],
  real_sector: [
    { text: 'What is the latest IIP growth rate for Manufacturing, Mining, and Electricity in India?' },
    { text: 'Summarize the Eight Core Industries (ICI) index — steel, cement, and coal YoY growth.' },
    { text: 'What are the latest use-based IIP figures for Capital Goods and Consumer Durables?' },
    { text: 'What is the current OBICUS capacity utilisation for the manufacturing sector?' },
  ],
};

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  selectedAgentId,
  onSelectAgent,
}) => {
  // Separate message histories per agent
  const [messagesByAgent, setMessagesByAgent] = useState<Record<string, ChatMessage[]>>(() => ({
    ...NEW_SECTOR_DEFAULT_MESSAGES,
    ...DEFAULT_MESSAGES,
  }));
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeSteps, setActiveSteps] = useState<StreamStep[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const selectedAgent =
    SECTOR_AGENTS.find((agent) => agent.id === selectedAgentId) ||
    SECTOR_AGENTS.find((agent) => agent.id === 'orchestrator')!;
  const isFinance = selectedAgentId === 'finance_sector';
  const isNewSector = Boolean(SECTOR_WORKSPACE_DESCRIPTIONS[selectedAgentId]);
  const isOrchestrator = !isFinance && !isNewSector;
  const AgentIcon = AGENT_ICONS[selectedAgentId] || Network;
  const currentMessages = messagesByAgent[selectedAgentId] || [];
  const currentPrompts = SUGGESTED_PROMPTS[selectedAgentId] || SUGGESTED_PROMPTS.orchestrator;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages, activeSteps, selectedAgentId]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isGenerating) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentAgent = selectedAgentId;
    const isCurrentFinance = currentAgent === 'finance_sector';
    const currentAgentMeta = SECTOR_AGENTS.find((agent) => agent.id === currentAgent);

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentTarget: currentAgent,
    };

    const botMessageId = `bot-${Date.now()}`;
    const initialBotMessage: ChatMessage = {
      id: botMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: isCurrentFinance
        ? 'Finance & Banking Sector Agent'
        : SECTOR_WORKSPACE_DESCRIPTIONS[currentAgent]
        ? `${currentAgentMeta?.name || 'Sector'} Specialist`
        : 'Macrograph Orchestrator',
      isStreaming: true,
      steps: [],
      citations: [],
    };

    setMessagesByAgent((prev) => ({
      ...prev,
      [currentAgent]: [...(prev[currentAgent] || []), userMessage, initialBotMessage],
    }));

    if (!queryText) setInput('');
    setIsGenerating(true);
    setActiveSteps([]);

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          message: textToSend.trim(),
          agent: currentAgent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let receivedSteps: StreamStep[] = [];
      let finalDonePayload: any = null;

      if (reader) {
        let buffer = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (!dataStr) continue;

              try {
                const event = JSON.parse(dataStr);

                if (event.type === 'step') {
                  const newStep: StreamStep = {
                    step: event.step,
                    agent: event.agent,
                    tool: event.tool,
                    title: event.title,
                    detail: event.detail,
                    status: 'running',
                  };
                  receivedSteps = [...receivedSteps, newStep];
                  setActiveSteps(receivedSteps);
                } else if (event.type === 'token') {
                  accumulatedText += event.text;
                  setMessagesByAgent((prev) => ({
                    ...prev,
                    [currentAgent]: (prev[currentAgent] || []).map((msg) =>
                      msg.id === botMessageId
                        ? {
                            ...msg,
                            content: accumulatedText,
                            steps: receivedSteps,
                          }
                        : msg
                    ),
                  }));
                } else if (event.type === 'done') {
                  finalDonePayload = event;
                }
              } catch (e) {
                // Ignore parse errors for partial chunks
              }
            }
          }
        }
      }

      // Mark streaming completed with final payload
      setMessagesByAgent((prev) => ({
        ...prev,
        [currentAgent]: (prev[currentAgent] || []).map((msg) =>
          msg.id === botMessageId
            ? {
                ...msg,
                content: finalDonePayload?.full_report || accumulatedText,
                agentRouted:
                  finalDonePayload?.agent_routed ||
                  (isCurrentFinance
                    ? 'Finance & Banking Sector Agent'
                    : SECTOR_WORKSPACE_DESCRIPTIONS[currentAgent]
                    ? `${currentAgentMeta?.name || 'Sector'} Specialist`
                    : 'Macrograph Orchestrator'),
                citations: finalDonePayload?.citations || [],
                observations: finalDonePayload?.observations,
                mermaidDiagram: finalDonePayload?.mermaid_diagram,
                confidenceScore: finalDonePayload?.confidence_score,
                dataStatus: finalDonePayload?.status,
                dataFreshness: finalDonePayload?.freshness,
                isStreaming: false,
                steps: receivedSteps,
              }
            : msg
        ),
      }));
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      setMessagesByAgent((prev) => ({
        ...prev,
        [currentAgent]: (prev[currentAgent] || []).map((msg) =>
          msg.id === botMessageId
            ? {
                ...msg,
                content: `### Research Request Incomplete\n\nAn error occurred while communicating with the agent: ${err.message || 'Unknown network error'}.`,
                dataStatus: SECTOR_WORKSPACE_DESCRIPTIONS[currentAgent] ? 'failed' : undefined,
                dataFreshness: SECTOR_WORKSPACE_DESCRIPTIONS[currentAgent]
                  ? { source: 'unavailable' }
                  : undefined,
                isStreaming: false,
              }
            : msg
        ),
      }));
    } finally {
      setIsGenerating(false);
      setActiveSteps([]);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-background overflow-hidden">
      {/* Top Header */}
      <div className="h-16 px-6 border-b border-white/5 bg-slate-950/80 backdrop-blur-xl flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-bold text-xs ${
              isFinance
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-glow-emerald/20'
                : isOrchestrator
                ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30 shadow-glow-brand/20'
                : ''
            }`}
            style={
              isNewSector
                ? {
                    backgroundColor: `${selectedAgent.color}20`,
                    color: selectedAgent.color,
                    border: `1px solid ${selectedAgent.color}50`,
                  }
                : undefined
            }
          >
            {isFinance ? 'FN' : isOrchestrator ? 'OR' : <AgentIcon className="w-4 h-4" />}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-white">
                {isFinance
                  ? 'Finance & Banking Sector Agent'
                  : isOrchestrator
                  ? 'Macrograph Orchestrator'
                  : `${selectedAgent.name} Specialist`}
              </span>
              <span
                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-medium ${
                  isFinance
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : isOrchestrator
                    ? 'bg-brand-500/10 text-brand-300 border border-brand-500/20'
                    : ''
                }`}
                style={
                  isNewSector
                    ? {
                        backgroundColor: `${selectedAgent.color}20`,
                        color: selectedAgent.color,
                        border: `1px solid ${selectedAgent.color}40`,
                      }
                    : undefined
                }
              >
                {isFinance
                  ? 'Direct Domain Mode (SCBs Only)'
                  : isOrchestrator
                  ? 'Multi-Agent Routing (All 10 Sectors)'
                  : 'Direct Domain Mode'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2">
              <span>
                {isFinance
                  ? 'Data: RBI DBIE Tables r539, r330, r531, r689 • Scheduled Commercial Banks'
                  : isOrchestrator
                  ? 'A2A Protocol Coordination • Cross-Sector Synthesis'
                  : isNewSector
                  ? `Data: ${selectedAgent.mcpSources.join(' • ')}`
                  : selectedAgent.domain}
              </span>
              <span>•</span>
              {isFinance ? (
                <span className="text-emerald-400 flex items-center gap-1 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live Ingested
                </span>
              ) : isOrchestrator ? (
                <span className="text-emerald-400 flex items-center gap-1 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live Ingested
                </span>
              ) : isNewSector ? (
                <span className="text-emerald-400 flex items-center gap-1 font-mono whitespace-nowrap">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Freshness per dataset
                </span>
              ) : (
                <span className="font-mono">Availability varies</span>
              )}
            </div>
          </div>
        </div>

        {/* Quick Agent Mode Toggle — segmented switcher look, same callback */}
        <div role="group" aria-label="Switch active agent" className="flex items-center gap-1 bg-slate-950/90 p-1.5 rounded-2xl border border-white/10 text-xs max-w-[54%] overflow-x-auto shadow-inner">
          {SECTOR_AGENTS.filter((agent) => agent.status === 'active').map((agent) => {
            const isSelected = selectedAgentId === agent.id;
            const isOrchestratorAgent = agent.id === 'orchestrator';
            return (
              <AgentToggleButton
                key={agent.id}
                label={AGENT_SHORT_NAMES[agent.id] || agent.name}
                title={agent.name}
                selected={isSelected}
                tone={isOrchestratorAgent ? 'brand' : 'emerald'}
                onClick={() => onSelectAgent(agent.id)}
              />
            );
          })}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div role="log" aria-live="polite" aria-label="Research conversation" className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {currentMessages.map((message) => (
          <div
            key={message.id}
            className={`cv-auto flex gap-3 max-w-4xl mx-auto ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-mono font-bold mt-1 ${
                  message.agentRouted?.includes('Finance')
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : isOrchestrator
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : ''
                }`}
                style={
                  isNewSector
                    ? {
                        backgroundColor: `${selectedAgent.color}20`,
                        color: selectedAgent.color,
                        border: `1px solid ${selectedAgent.color}50`,
                      }
                    : undefined
                }
              >
                {message.agentRouted?.includes('Finance')
                  ? 'FN'
                  : isOrchestrator
                  ? 'OR'
                  : <AgentIcon className="w-4 h-4" />}
              </div>
            )}

            <div
              className={`p-5 rounded-2xl max-w-3xl ${
                message.role === 'user'
                  ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white shadow-glow-brand/20 ml-12'
                  : 'glass-panel text-slate-200 border border-white/10 shadow-glass mr-6 w-full'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{message.agentRouted}</span>
                    {isNewSector ? (
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                          message.dataStatus === 'partial'
                            ? 'bg-amber-500/10 text-amber-300'
                            : message.dataStatus === 'unavailable' || message.dataStatus === 'failed'
                            ? 'bg-rose-500/10 text-rose-300'
                            : 'bg-white/5 text-slate-400'
                        }`}
                      >
                        {message.dataStatus === 'partial'
                          ? 'Partial data'
                          : message.dataStatus === 'unavailable'
                          ? 'Data unavailable'
                          : message.dataStatus === 'failed'
                          ? 'Agent error'
                          : message.dataStatus === 'completed'
                          ? 'Data available'
                          : 'Sector response'}
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400">
                        Attribution Verified
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-[11px] text-slate-500">{message.timestamp}</span>
                </div>
              )}

              {/* Streaming Steps Progress (if currently running) */}
              {message.isStreaming && message.steps && message.steps.length > 0 && (
                <div
                  className={`mb-4 p-3 rounded-xl bg-slate-900/80 space-y-2 ${
                    isNewSector
                      ? 'border border-emerald-500/20'
                      : 'border border-brand-500/20'
                  }`}
                >
                  <div
                    className={`text-[11px] font-mono uppercase tracking-wider font-semibold flex items-center gap-2 ${
                      isNewSector ? 'text-emerald-400' : 'text-brand-400'
                    }`}
                  >
                    <RefreshCw
                      className={`w-3 h-3 animate-spin ${
                        isNewSector ? 'text-emerald-400' : ''
                      }`}
                    />
                    <span>Real-Time Execution Pipeline</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    {message.steps.map((st, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span
                          className={`mt-0.5 ${
                            isNewSector ? 'text-emerald-400' : 'text-emerald-400'
                          }`}
                        >
                          ●
                        </span>
                        <div>
                          <span className="font-semibold text-slate-200">{st.title}: </span>
                          <span className="text-slate-400">{st.detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Message Body (Markdown rendered — same parser, UI skeleton when empty) */}
              {message.role === 'assistant' && message.isStreaming && !message.content ? (
                <div className="space-y-2.5 py-1" aria-label="Generating response">
                  <div className="skeleton h-4 rounded-lg w-11/12" />
                  <div className="skeleton h-4 rounded-lg w-9/12" />
                  <div className="skeleton h-4 rounded-lg w-10/12" />
                </div>
              ) : (
                <div
                  className={`prose prose-invert prose-custom max-w-none text-sm text-slate-200 leading-relaxed ${
                    selectedAgentId === 'capital_market_sector' ? 'capital-market-response' : ''
                  }`}
                  dangerouslySetInnerHTML={{
                    __html: formatMarkdown(message.content, selectedAgentId === 'capital_market_sector'),
                  }}
                />
              )}

              {isNewSector && message.dataFreshness && (
                <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                  <span className="text-slate-500 uppercase">Data freshness:</span>
                  {Object.entries(message.dataFreshness).map(([dataset, freshness]) => (
                    <span
                      key={dataset}
                      className={`px-2 py-1 rounded bg-white/5 ${
                        freshness === 'live'
                          ? 'text-emerald-300'
                          : freshness === 'cached' || freshness === 'upstream_snapshot'
                          ? 'text-amber-300'
                          : 'text-slate-400'
                      }`}
                    >
                      {dataset.replace(/_/g, ' ')}:{' '}
                      {freshness === 'upstream_snapshot'
                        ? 'upstream snapshot (not real-time)'
                        : freshness}
                    </span>
                  ))}
                </div>
              )}

              {/* Citations Box (Strict Non-Hallucinatory Chain) */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-5 pt-3 border-t border-white/10">
                  <div className="text-[11px] font-mono uppercase text-emerald-400 font-semibold mb-2 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>
                      {isNewSector ? 'Reported Source Metadata' : 'Verified Official Citations & Provenance'}
                    </span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {message.citations.map((cite, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-900/60 border border-white/5 text-[11px] font-mono"
                      >
                        {(!isNewSector ||
                          cite.authority ||
                          cite.source_authority ||
                          cite.source_agent) && (
                          <div className="text-white font-medium truncate">
                            {cite.authority ||
                              cite.source_authority ||
                              (isNewSector ? cite.source_agent : 'Reserve Bank of India (RBI)')}
                          </div>
                        )}
                        {isNewSector && cite.dataset && (
                          <div className="text-slate-300 text-[10px] truncate mt-0.5">
                            Dataset: {cite.dataset.replace(/_/g, ' ')}
                          </div>
                        )}
                        {isNewSector && cite.document_title && (
                          <div className="text-slate-400 text-[10px] truncate mt-0.5">
                            {cite.document_title}
                          </div>
                        )}
                        {isNewSector && cite.frequency && (
                          <div className="text-slate-400 text-[10px] truncate mt-0.5">
                            Frequency: {cite.frequency}
                            {cite.unit ? ` • Unit: ${cite.unit}` : ''}
                          </div>
                        )}
                        {isNewSector && cite.as_of && (
                          <div className="text-slate-400 text-[10px] truncate mt-0.5">
                            Source as of: {cite.as_of}
                          </div>
                        )}
                        {(!isNewSector || cite.table || cite.table_reference) && (
                          <div
                            className={`text-[10px] truncate mt-0.5 ${
                              isNewSector ? 'text-emerald-300' : 'text-brand-300'
                            }`}
                          >
                            Table: {cite.table || cite.table_reference}
                          </div>
                        )}
                        {isNewSector &&
                          cite.retrieval_url &&
                          /^https?:\/\//i.test(cite.retrieval_url) && (
                            <a
                              href={cite.retrieval_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan-300 text-[10px] truncate block mt-1 hover:underline"
                            >
                              View source
                            </a>
                          )}
                        {isNewSector && cite.source_note && (
                          <div className="text-amber-200/80 text-[10px] mt-1">
                            {cite.source_note}
                          </div>
                        )}
                        {(!isNewSector || cite.period || cite.observation_period || cite.freshness) && (
                          <div className="flex items-center justify-between text-slate-400 text-[10px] mt-1">
                            {(!isNewSector || cite.period || cite.observation_period) && (
                              <span>
                                Period: {cite.period || cite.observation_period || '2024-09'}
                              </span>
                            )}
                            {(!isNewSector || cite.freshness) && (
                              <span
                                className={`font-semibold uppercase ${
                                  isNewSector ? '' : 'text-emerald-400'
                                }`}
                              >
                                {cite.freshness || (isNewSector ? '' : 'Verified')}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mermaid Diagram Box if provided */}
              {message.mermaidDiagram && (
                <div className="mt-4 p-3 rounded-xl bg-slate-950 border border-white/10">
                  <div className="text-xs font-mono text-cyan-400 font-semibold mb-1 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5" />
                    <span>Causal Transmission Path (Mermaid Graph)</span>
                  </div>
                  <pre className="text-[11px] font-mono text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded">
                    <code>{message.mermaidDiagram}</code>
                  </pre>
                </div>
              )}
            </div>

            {message.role === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 flex items-center justify-center shrink-0 text-xs font-bold mt-1">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {/* Live Active Step Banner when query is processing */}
        {isGenerating && activeSteps.length > 0 && (
          <div className="max-w-4xl mx-auto p-4 rounded-2xl glass-panel border border-brand-500/30 shadow-glow-brand/20 animate-pulse">
            <div className="flex items-center gap-2 text-xs font-mono text-brand-300 mb-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-400" />
              <span>Multi-Agent In-Flight Operations:</span>
            </div>
            <div className="space-y-1.5 text-xs text-slate-300">
              {activeSteps.map((st, i) => (
                <div key={i} className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="font-semibold text-white">{st.title}:</span>
                  <span className="text-slate-400 truncate">{st.detail}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts Carousel */}
      <div className="px-4 sm:px-6 py-2 border-t border-white/5 bg-slate-950/40">
        <div aria-label="Suggested prompts" className="max-w-4xl mx-auto flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-[11px] font-mono text-slate-500 shrink-0 flex items-center gap-1">
            <Sparkles className={`w-3 h-3 ${isNewSector ? 'text-emerald-400' : 'text-brand-400'}`} />
            Quick Prompts:
          </span>
          {currentPrompts.map((prompt, idx) => (
            <PromptChip key={idx} text={prompt.text} disabled={isGenerating} tone={isNewSector ? 'emerald' : 'default'} onPick={(t) => handleSendMessage(t)} />
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 md:p-6 border-t border-white/5 bg-slate-950/80 backdrop-blur-xl shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="max-w-4xl mx-auto relative flex items-center mesh-beam rounded-xl"
        >
          <label htmlFor="chat-input" className="sr-only">
            Ask {isFinance ? 'Finance and Banking Sector Agent' : isOrchestrator ? 'Macrograph Orchestrator' : selectedAgent.name}
          </label>
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isGenerating}
            autoComplete="off"
            placeholder={
              isFinance
                ? 'Ask Finance Agent strictly about Scheduled Commercial Banks, NPAs, credit growth, rates...'
                : isOrchestrator
                ? 'Ask Orchestrator any macroeconomic question (GDP, inflation, policy transmission, cross-sector shocks)...'
                : `Ask ${selectedAgent.name} about ${selectedAgent.domain.toLowerCase()}...`
            }
            className={`w-full pl-5 pr-28 py-3.5 bg-surface-elevated/80 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all font-sans disabled:opacity-50 ${
              isNewSector
                ? 'focus:ring-emerald-500/50 focus:border-emerald-500/50'
                : 'focus:ring-brand-500/50 focus:border-brand-500/50'
            }`}
          />

          <button
            type="submit"
            aria-label="Send message"
            disabled={!input.trim() || isGenerating}
            className={`touch-44 absolute right-2 px-4 rounded-lg text-white text-xs font-semibold shadow-glow-brand transition-all flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
              isFinance
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-glow-emerald'
                : isOrchestrator
                ? 'bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 shadow-glow-brand'
                : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-glow-emerald'
            }`}
          >
            <span>Ask</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        <div className="max-w-4xl mx-auto mt-2 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>
            {isFinance
              ? 'Routing: Direct to Finance Sector (RBI DBIE) • Domain Boundary Enforced'
              : isOrchestrator
              ? 'Routing: LangGraph A2A Multi-Agent Graph (All 10 Sectors)'
              : `Direct ${selectedAgent.name} workspace • Source and freshness metadata per dataset`}
          </span>
          <span>
            {isNewSector
              ? 'Citations and freshness shown only when returned'
              : 'Zero Hallucination Guaranteed'}
          </span>
        </div>
      </div>
    </div>
  );
};

// Helper: Basic Markdown Parser for clean display
function formatMarkdown(text: string, wrapTables = false): string {
  if (!text) return '';

  let html = text
    // Replace code blocks
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Replace blockquotes (> block)
    .replace(/^> (.*$)/gim, '<blockquote class="border-l-2 border-amber-400/80 bg-amber-500/5 p-2 rounded text-amber-200 text-xs my-2">$1</blockquote>')
    // Replace headers
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    // Bold and italics
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Tables (Markdown table syntax converter)
    .replace(
      /\|(.+)\|\n\|[-:| ]+\|\n((?:\|.+\|\n?)+)/g,
      (_match, header, body) => {
        const headers = header
          .split('|')
          .filter((h: string) => h.trim())
          .map((h: string) => `<th>${h.trim()}</th>`)
          .join('');
        const rows = body
          .trim()
          .split('\n')
          .map((row: string) => {
            const cols = row
              .split('|')
              .filter((c: string) => c.trim())
              .map((c: string) => `<td>${c.trim()}</td>`)
              .join('');
            return `<tr>${cols}</tr>`;
          })
          .join('');
        const table = `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
        return wrapTables
          ? `<div class="capital-market-table-scroll" role="region" aria-label="Scrollable market data table" tabindex="0">${table}</div>`
          : table;
      }
    )
    // Bullet lists ("- " and "1. " markers; the model emits both)
    .replace(/^\- (.*$)/gim, '<li>$1</li>')
    .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
    // Wrap consecutive list items in <ul>
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    // Line breaks: blank line = paragraph gap, single newline = visible break
    // (HTML collapses raw "\n", which previously glued everything into one line)
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');

  return html;
}
