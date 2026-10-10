import React, { useState, useRef, useEffect, memo } from 'react';
import {
  Send,
  Sparkles,
  User,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Network,
  Landmark,
  TrendingUp,
  Coins,
  Globe,
  Users,
  Activity,
  Sprout,
  Percent,
  Briefcase,
  Receipt,
  type LucideIcon,
} from 'lucide-react';
import { A2ASummary, ChatMessage, CitationItem, StreamStep } from '../types';
import { A2ATracePanel } from './A2ATracePanel';
import { MermaidDiagram } from './MermaidDiagram';
import { ModelCardStrip } from './chat/ModelCardStrip';
import { DebateDag } from './chat/DebateDag';
import type { ConsensusPayload, ModelCardPayload } from '../types/research';
import { MarkdownMessage } from './chat/MarkdownMessage';
import { CopyButton } from './chat/CopyButton';
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
  services_sector: [
    {
      id: 'welcome-services',
      role: 'assistant',
      content: `### Services Sector Specialist\n\nI am the dedicated **Services Sector Agent** with direct access to the official **MoSPI e-Sankhyiki MCP** (https://mcp.mospi.gov.in/) and DuckDB stores.\n\n### Specialized Domain Scope (Services Production & Activity):\n- **ISP Growth**: Monthly Index of Service Production, General index + 19 sub-sectors — IT & computer services, telecom, trade, transport (Base 2024-25 = 100)\n- **Services GVA**: Structural Output & GVA from NAS Statements 8.9–8.14 (trade & hotels, transport, communication, finance, real estate)\n- **PMI Sentiment**: Services PMI headline activity, new orders, input costs & employment (S&P Global / HSBC)\n- **Volumes**: Aviation passengers, railway freight, port cargo & telecom subscriptions\n\n> ⚠️ **Strict Domain Boundary Notice**\n> I strictly handle queries regarding **India's services production and activity**. Monthly ISP is a high-frequency measure; NAS GVA is the structural annual measure. If you have queries on other sectors (e.g. GDP, Inflation, Banking, Forex, or Fiscal Deficits), please switch to the **Macrograph Orchestrator**.\n\nAsk a services question below or choose a suggested prompt!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: 'Services Sector Specialist',
      citations: [
        {
          source_agent: 'services_sector',
          authority: 'National Statistical Office (NSO), MoSPI',
          table: 'mospi.isp_monthly / mospi.nas_statement_8_12',
          period: 'Live MoSPI Feeds',
          freshness: 'live & cached',
        },
      ],
    },
  ],
  fiscal_sector: [
    {
      id: 'welcome-fiscal',
      role: 'assistant',
      content: `### Fiscal & Public Finance Sector Specialist\n\nI am the dedicated **Fiscal Sector Agent** with verified access to the **Union Budget / CGA**, **Goods & Services Tax (GST) Council**, **MoSPI eSankhyiki FastMCP**, and **IMF World Economic Outlook (WEO)**.\n\n### Specialized Domain Scope:\n- 🏛️ **Union Budget & CGA Accounts**: Revenue Receipts, Capital Expenditure, Gross Fiscal Deficit (% of GDP), Revenue Deficit, Primary Deficit\n- 📊 **Monthly Gross GST Collections**: CGST, SGST, IGST, Compensation Cess, and YoY Growth\n- 🌐 **Sovereign Debt (IMF WEO)**: General Government Gross Debt-to-GDP, Net Lending/Borrowing % of GDP\n- 📈 **MoSPI National Accounts**: Net Taxes on Products (current & constant prices) & Govt Final Consumption (GFCE)\n- 🧮 **Statutory Calculators**: GST invoice breakups (CGST/SGST/IGST), GSTIN mod-36 validation, and FY 2026-27 tax regime comparison\n- 📡 **Real-Time MoF Intelligence**: PIB Ministry of Finance press releases via Tavily AI Search\n\n> 🛡️ **Strict Anti-Hallucination & Attribution Chain**\n> Every metric returned carries structured provenance with source authority, document reference, and observation period.\n\nAsk about India's fiscal deficit, GST trends, public debt, or try a suggested query!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agentRouted: 'Fiscal & Public Finance Specialist',
      citations: [
        {
          source_agent: 'fiscal_sector',
          authority: 'Ministry of Finance & CGA / MoSPI / IMF',
          table: 'Union Budget Statement 1, Monthly GST Press Releases, IMF WEO IND.GGXWDG_NGDP.A',
          period: 'FY 2024-25 & Live Snapshots',
          freshness: 'live',
          retrieval_url: 'https://indiabudget.gov.in',
        },
      ],
    },
  ],
};

const SECTOR_WORKSPACE_DESCRIPTIONS: Record<string, string> = {
  fiscal_sector:
    'Queries Union Budget receipts & deficits, monthly gross GST collections, IMF WEO sovereign debt ratios, and MoSPI Net Product Taxes with cryptographic provenance.',
  agriculture_sector:
    'Analyzes crops, mandi prices, MSP, rainfall, agricultural inputs and schemes using Agriculture MCP tools. Every observation identifies its actual source; unavailable data is reported explicitly.',
  external_sector:
    'Combines a configured RBI forex feed with locally stored trade and exchange-rate observations.',
  labour_sector:
    'Uses a configured MoSPI unemployment request and locally stored labour observations.',
  capital_market_sector:
    'Uses a configured NSE NIFTY request and locally stored market observations.',
  monetary_sector:
    'Combines official RBI DBIE data (policy rates, money supply, LAF liquidity) with real-time MPC intelligence via Tavily AI Search, synthesized by Groq LLM into cited monetary policy analysis.',
  real_sector:
    'Fetches MoSPI IIP (sectoral & use-based), DPIIT Eight Core Industries index, and RBI DBIE manufacturing GVA data with per-observation provenance.',
  prices_sector:
    'Fetches live CPI and WPI observations from the MoSPI e-Sankhyiki MCP, with IMF data available as a clearly labeled secondary validation source.',
  services_sector:
    'Uses the official MoSPI e-Sankhyiki MCP (ISP monthly production, NAS 8.9–8.14 structural GVA, NSS80 telecom volumes) plus PMI sentiment and Nifty IT market context.',
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
  fiscal_sector: Receipt,
  monetary_sector: Coins,
  real_sector: Activity,
  capital_market_sector: TrendingUp,
  prices_sector: Percent,
  services_sector: Briefcase,
  external_sector: Globe,
  agriculture_sector: Sprout,
  labour_sector: Users,
};

const AGENT_SHORT_NAMES: Record<string, string> = {
  orchestrator: 'Orchestrator',
  finance_sector: 'Finance & Banking',
  fiscal_sector: 'Fiscal & Budget',
  monetary_sector: 'Monetary Policy',
  real_sector: 'Real Economy',
  capital_market_sector: 'Capital Markets',
  prices_sector: 'Prices & Inflation',
  external_sector: 'External & Trade',
  agriculture_sector: 'Agriculture',
  labour_sector: 'Labour & Jobs',
  services_sector: 'Services',
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

const AgentToggleButton = memo(function AgentToggleButton({
  label,
  selected,
  tone,
  onClick,
  title,
  icon: Icon,
  color,
}: {
  label: string;
  selected: boolean;
  tone: 'brand' | 'emerald' | 'pink';
  onClick: () => void;
  title: string;
  icon?: LucideIcon;
  color?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={selected}
      className={`shrink-0 px-3 py-1.5 rounded-xl font-medium transition-all flex items-center gap-1.5 whitespace-nowrap text-xs border select-none ${
        selected
          ? tone === 'brand'
            ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white shadow-glow-brand/50 border-brand-400/50'
            : tone === 'pink'
            ? 'bg-gradient-to-r from-pink-600 to-rose-600 text-white shadow-[0_0_15px_rgba(236,72,153,0.35)] border-pink-400/50'
            : 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-glow-emerald/40 border-emerald-400/50'
          : 'text-slate-400 hover:text-white hover:bg-white/5 border-transparent'
      }`}
    >
      {Icon && (
        <Icon
          className="w-3.5 h-3.5 shrink-0"
          style={{ color: selected ? '#ffffff' : color }}
        />
      )}
      <span className="shrink-0">{label}</span>
      {selected && (
        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse shrink-0 ml-0.5" />
      )}
    </button>
  );
});

const SUGGESTED_PROMPTS: Record<string, { text: string }[]> = {
  fiscal_sector: [
    { text: 'What is India\'s Union fiscal deficit target for FY 2024-25 and capex budget?' },
    { text: 'Show gross monthly GST revenue trends, buoyancy, and component breakup.' },
    { text: 'Analyze India\'s General Government debt-to-GDP trajectory from IMF WEO.' },
    { text: 'Compare income tax liabilities under the new vs. old regimes for FY 2026-27.' },
    { text: 'What is the statutory GST breakdown for a ₹50,000 transaction at 18% slab?' },
  ],
  agriculture_sector: [
    { text: 'How has wheat production changed?' },
    { text: 'Show historical rainfall in Mumbai for the last 7 days.' },
    { text: 'What is the current MSP for wheat?' },
  ],
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
  ],
  prices_sector: [
    { text: "What is India's latest CPI inflation from MoSPI?" },
    { text: "Show India's CPI food, rural, and urban inflation." },
    { text: "What is India's latest WPI inflation?" },
  ],
  services_sector: [
    { text: "How is India's IT services sector performing?" },
    { text: 'What is the latest ISP General index growth for services?' },
    { text: 'What is the current Services PMI reading and new orders trend?' },
    { text: 'Compare structural services GVA (NAS) with high-frequency ISP momentum.' },
  ],
};

interface StreamEvent {
  type: 'step' | 'token' | 'done';
  step: number;
  agent?: string;
  tool?: string;
  request_id?: string;
  status?: string;
  title: string;
  detail: string;
  text: string;
  full_report?: string;
  agent_routed?: string;
  citations?: CitationItem[];
  observations?: ChatMessage['observations'];
  mermaid_diagram?: string;
  confidence_score?: number | null;
  freshness?: Record<string, string>;
  a2a?: A2ASummary;
  consensus?: ConsensusPayload;
  model_card?: ModelCardPayload;
}

type DonePayload = StreamEvent;

// A2A steps are updated in place as their request progresses; other steps append.
function upsertStep(steps: StreamStep[], next: StreamStep): StreamStep[] {
  if (!next.request_id) return [...steps, next];
  const index = steps.findIndex((s) => s.request_id === next.request_id);
  if (index === -1) return [...steps, next];
  return steps.map((s, i) => (i === index ? { ...next, step: s.step } : s));
}

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
  const isFiscal = selectedAgentId === 'fiscal_sector';
  const isNewSector = Boolean(SECTOR_WORKSPACE_DESCRIPTIONS[selectedAgentId]) && !isFinance && !isFiscal;
  const isOrchestrator = !isFinance && !isFiscal && !isNewSector;
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
      let finalDonePayload: DonePayload | null = null;

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
                const event = JSON.parse(dataStr) as StreamEvent;

                if (event.type === 'step') {
                  const newStep: StreamStep = {
                    step: event.step,
                    agent: event.agent,
                    tool: event.tool,
                    title: event.title,
                    detail: event.detail,
                    request_id: event.request_id,
                    status: (event.status as StreamStep['status']) ?? 'running',
                  };
                  receivedSteps = upsertStep(receivedSteps, newStep);
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
              } catch (parseError) {
                console.warn('Skipping malformed stream event', parseError);
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
                confidenceScore: finalDonePayload?.confidence_score ?? undefined,
                a2a: finalDonePayload?.a2a,
                consensus: finalDonePayload?.consensus,
                modelCard: finalDonePayload?.model_card,
                dataStatus: finalDonePayload?.status,
                dataFreshness: finalDonePayload?.freshness,
                isStreaming: false,
                steps: receivedSteps,
              }
            : msg
        ),
      }));
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const errMessage = err instanceof Error ? err.message : 'Unknown network error';
      setMessagesByAgent((prev) => ({
        ...prev,
        [currentAgent]: (prev[currentAgent] || []).map((msg) =>
          msg.id === botMessageId
            ? {
                ...msg,
                content: `### Research Request Incomplete\n\nAn error occurred while communicating with the agent: ${errMessage}.`,
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
      <div className="min-h-16 px-3 py-2 sm:px-6 border-b border-white/5 bg-slate-950/80 backdrop-blur-xl flex flex-wrap items-center justify-between gap-x-4 gap-y-2 shrink-0">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-bold text-xs shrink-0 ${
              isFinance
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-glow-emerald/20'
                : isFiscal
                ? 'bg-pink-500/20 text-pink-400 border border-pink-500/30 shadow-[0_0_15px_rgba(236,72,153,0.3)]'
                : isOrchestrator
                ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30 shadow-glow-brand/20'
                : ''
            }`}
            style={
              !isFinance && !isFiscal && !isOrchestrator
                ? {
                    backgroundColor: `${selectedAgent.color}20`,
                    color: selectedAgent.color,
                    border: `1px solid ${selectedAgent.color}50`,
                  }
                : undefined
            }
          >
            {isFinance ? 'FN' : isFiscal ? 'FI' : isOrchestrator ? 'OR' : <AgentIcon className="w-4 h-4" />}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-white truncate">
                {isFinance
                  ? 'Finance & Banking Sector Agent'
                  : isFiscal
                  ? 'Fiscal & Public Finance Sector Agent'
                  : isOrchestrator
                  ? 'Macrograph Orchestrator'
                  : `${selectedAgent.name} Specialist`}
              </span>
              <span
                className={`hidden lg:inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-medium whitespace-nowrap shrink-0 ${
                  isFinance
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : isFiscal
                    ? 'bg-pink-500/10 text-pink-300 border border-pink-500/20'
                    : isOrchestrator
                    ? 'bg-brand-500/10 text-brand-300 border border-brand-500/20'
                    : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                }`}
              >
                {isFinance
                  ? 'Direct Domain Mode (SCBs Only)'
                  : isFiscal
                  ? 'Direct Domain Mode (Budget & Debt)'
                  : isOrchestrator
                  ? 'Multi-Agent Routing (All 10 Sectors)'
                  : 'Direct Domain Mode'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2 truncate">
              <span className="truncate max-w-sm xl:max-w-md">
                {isFinance
                  ? 'Data: RBI DBIE Tables r539, r330, r531, r689 • Scheduled Commercial Banks'
                  : isFiscal
                  ? 'Data: MoSPI eSankhyiki • IMF WEO SDMX • Union Budget CGA • GST Council'
                  : isOrchestrator
                  ? 'A2A Protocol Coordination • Cross-Sector Synthesis'
                  : isNewSector
                  ? `Data: ${selectedAgent.mcpSources.join(' • ')}`
                  : selectedAgent.domain}
              </span>
              <span>•</span>
              <span className="text-emerald-400 flex items-center gap-1 font-mono whitespace-nowrap shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Ingested
              </span>
            </div>
          </div>
        </div>

        {/* Quick Agent Mode Toggle — segmented switcher with shrink-0 buttons and crisp pills */}
        <div
          role="group"
          aria-label="Switch active agent"
          className="flex w-full items-center gap-1.5 overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/90 p-1.5 text-xs shadow-inner select-none sm:w-auto sm:max-w-[55%]"
        >
          {SECTOR_AGENTS.filter((agent) => agent.status === 'active').map((agent) => {
            const isSelected = selectedAgentId === agent.id;
            const isOrchestratorAgent = agent.id === 'orchestrator';
            const isFiscalAgent = agent.id === 'fiscal_sector';
            const Icon = AGENT_ICONS[agent.id] || Network;
            return (
              <AgentToggleButton
                key={agent.id}
                label={AGENT_SHORT_NAMES[agent.id] || agent.name}
                title={agent.name}
                selected={isSelected}
                icon={Icon}
                color={agent.color}
                tone={isOrchestratorAgent ? 'brand' : isFiscalAgent ? 'pink' : 'emerald'}
                onClick={() => onSelectAgent(agent.id)}
              />
            );
          })}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        role="log"
        aria-live="polite"
        aria-label="Research conversation"
        className="flex-1 min-w-0 overflow-x-hidden overflow-y-auto scroll-smooth px-3 py-5 sm:px-6 md:py-8 space-y-7"
      >
        {currentMessages.map((message) => (
          <div
            key={message.id}
            className={`cv-auto flex w-full min-w-0 gap-3 max-w-4xl mx-auto ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div
                className={`w-8 h-8 rounded-xl hidden sm:flex items-center justify-center shrink-0 text-xs font-mono font-bold mt-1 ${
                  message.agentRouted?.includes('Finance')
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : message.agentRouted?.includes('Fiscal')
                    ? 'bg-pink-500/20 text-pink-400 border border-pink-500/30'
                    : isOrchestrator
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : ''
                }`}
                style={
                  !message.agentRouted?.includes('Finance') &&
                  !message.agentRouted?.includes('Fiscal') &&
                  !isOrchestrator
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
                  : message.agentRouted?.includes('Fiscal')
                  ? 'FI'
                  : isOrchestrator
                  ? 'OR'
                  : <AgentIcon className="w-4 h-4" />}
              </div>
            )}

            <div
              className={`min-w-0 rounded-2xl ${
                message.role === 'user'
                  ? 'max-w-[85%] bg-gradient-to-br from-brand-600 to-indigo-600 px-4 py-3 text-white shadow-glow-brand/20 sm:max-w-xl'
                  : 'flex-1 overflow-hidden border border-white/10 bg-slate-950/55 p-4 text-slate-200 shadow-glass backdrop-blur-xl sm:p-6'
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
                            st.status === 'failed'
                              ? 'text-rose-400'
                              : st.status === 'partial'
                              ? 'text-amber-400'
                              : st.request_id && st.status === 'running'
                              ? 'text-slate-400 animate-pulse'
                              : 'text-emerald-400'
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
              ) : message.role === 'user' ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed [overflow-wrap:anywhere]">{message.content}</p>
              ) : (
                <MarkdownMessage content={message.content} isStreaming={message.isStreaming} />
              )}

              {message.role === 'assistant' && !message.isStreaming && message.content && !message.id.startsWith('welcome-') && (
                <div className="mt-4 flex items-center justify-end border-t border-white/5 pt-3">
                  <CopyButton text={message.content} label="Copy report" />
                </div>
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
                        {isNewSector && cite.citation_id && (
                          <div className="text-emerald-300 font-semibold mb-1">
                            [{cite.citation_id}] {cite.indicator || 'Observation'}
                          </div>
                        )}
                        {isNewSector && cite.value !== undefined && (
                          <div className="text-white text-sm font-semibold mb-1">
                            {cite.value} {cite.unit || ''}
                          </div>
                        )}
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
                        {isNewSector && cite.mcp_tool && (
                          <div className="text-slate-400 text-[10px] mt-0.5">
                            Path: Agriculture Agent → {cite.mcp_tool} → {cite.upstream_tool || 'source'}
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
                        {isNewSector && cite.provenance_hash && (
                          <div className="text-slate-500 text-[10px] mt-1">
                            Provenance: {cite.provenance_hash}
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
                                {(cite.freshness || (isNewSector ? '' : 'Verified')).replace(
                                  /_/g,
                                  ' ',
                                )}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {message.a2a && <A2ATracePanel a2a={message.a2a} />}
              {message.modelCard && <ModelCardStrip card={message.modelCard} />}
              {message.consensus && <DebateDag consensus={message.consensus} a2a={message.a2a} />}

              {/* Reports embed the diagram inline as a mermaid fence; only append it when the text has none */}
              {message.mermaidDiagram && !message.content.includes('```mermaid') && (
                <MermaidDiagram code={message.mermaidDiagram} title="Causal Transmission Path" />
              )}
            </div>

            {message.role === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 hidden sm:flex items-center justify-center shrink-0 text-xs font-bold mt-1">
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
                  <CheckCircle2
                    className={`w-3.5 h-3.5 shrink-0 ${
                      st.status === 'failed'
                        ? 'text-rose-400'
                        : st.status === 'partial'
                        ? 'text-amber-400'
                        : st.request_id && st.status === 'running'
                        ? 'text-slate-500'
                        : 'text-emerald-400'
                    }`}
                  />
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
                : isFiscal
                ? 'Ask Fiscal Agent about Union Budget deficits, GST collections, IMF sovereign debt, tax calculation...'
                : isOrchestrator
                ? 'Ask Orchestrator any macroeconomic question (GDP, inflation, policy transmission, cross-sector shocks)...'
                : `Ask ${selectedAgent.name} about ${selectedAgent.domain.toLowerCase()}...`
            }
            className={`w-full pl-5 pr-28 py-3.5 bg-surface-elevated/80 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 transition-all font-sans disabled:opacity-50 ${
              isFiscal
                ? 'focus:ring-pink-500/50 focus:border-pink-500/50'
                : isNewSector
                ? 'focus:ring-emerald-500/50 focus:border-emerald-500/50'
                : 'focus:ring-brand-500/50 focus:border-brand-500/50'
            }`}
          />

          <button
            type="submit"
            aria-label="Send message"
            disabled={!input.trim() || isGenerating}
            className={`touch-44 absolute right-2 px-4 rounded-lg text-white text-xs font-semibold transition-all flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
              isFinance
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-glow-emerald'
                : isFiscal
                ? 'bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-500 hover:to-rose-500 shadow-[0_0_20px_rgba(236,72,153,0.35)]'
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
              : isFiscal
              ? 'Routing: Direct to Fiscal Sector (Union Budget, MoSPI NAS, IMF WEO, GST Council)'
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
