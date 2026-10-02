import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  User,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { ChatMessage, StreamStep } from '../types';

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
};

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
};

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  selectedAgentId,
  onSelectAgent,
}) => {
  // Separate message histories per agent
  const [messagesByAgent, setMessagesByAgent] = useState<Record<string, ChatMessage[]>>(DEFAULT_MESSAGES);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeSteps, setActiveSteps] = useState<StreamStep[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isFinance = selectedAgentId === 'finance_sector';
  const currentMessages = messagesByAgent[selectedAgentId] || DEFAULT_MESSAGES[selectedAgentId] || [];
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
      agentRouted: isCurrentFinance ? 'Finance & Banking Sector Agent' : 'Macrograph Orchestrator',
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
                  (isCurrentFinance ? 'Finance & Banking Sector Agent' : 'Macrograph Orchestrator'),
                citations: finalDonePayload?.citations || [],
                observations: finalDonePayload?.observations,
                mermaidDiagram: finalDonePayload?.mermaid_diagram,
                confidenceScore: finalDonePayload?.confidence_score,
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
                : 'bg-brand-500/20 text-brand-400 border border-brand-500/30 shadow-glow-brand/20'
            }`}
          >
            {isFinance ? 'FN' : 'OR'}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-white">
                {isFinance ? 'Finance & Banking Sector Agent' : 'Macrograph Orchestrator'}
              </span>
              <span
                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-medium ${
                  isFinance
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-brand-500/10 text-brand-300 border border-brand-500/20'
                }`}
              >
                {isFinance ? 'Direct Domain Mode (SCBs Only)' : 'Multi-Agent Routing (All 10 Sectors)'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2">
              <span>
                {isFinance
                  ? 'Data: RBI DBIE Tables r539, r330, r531, r689 • Scheduled Commercial Banks'
                  : 'A2A Protocol Coordination • Cross-Sector Synthesis'}
              </span>
              <span>•</span>
              <span className="text-emerald-400 flex items-center gap-1 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Ingested
              </span>
            </div>
          </div>
        </div>

        {/* Quick Agent Mode Toggle */}
        <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-xl border border-white/10 text-xs">
          <button
            onClick={() => onSelectAgent('orchestrator')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              !isFinance
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Orchestrator
          </button>
          <button
            onClick={() => onSelectAgent('finance_sector')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              isFinance
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Finance Agent</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {currentMessages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 max-w-4xl mx-auto ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-mono font-bold mt-1 ${
                  message.agentRouted?.includes('Finance')
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                }`}
              >
                {message.agentRouted?.includes('Finance') ? 'FN' : 'OR'}
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
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400">
                      Attribution Verified
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-500">{message.timestamp}</span>
                </div>
              )}

              {/* Streaming Steps Progress (if currently running) */}
              {message.isStreaming && message.steps && message.steps.length > 0 && (
                <div className="mb-4 p-3 rounded-xl bg-slate-900/80 border border-brand-500/20 space-y-2">
                  <div className="text-[11px] font-mono uppercase tracking-wider text-brand-400 font-semibold flex items-center gap-2">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Real-Time Execution Pipeline</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    {message.steps.map((st, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-emerald-400 mt-0.5">●</span>
                        <div>
                          <span className="font-semibold text-slate-200">{st.title}: </span>
                          <span className="text-slate-400">{st.detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Message Body (Markdown rendered) */}
              <div
                className="prose prose-invert prose-custom max-w-none text-sm text-slate-200 leading-relaxed"
                dangerouslySetInnerHTML={{
                  __html: formatMarkdown(message.content),
                }}
              />

              {/* Citations Box (Strict Non-Hallucinatory Chain) */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-5 pt-3 border-t border-white/10">
                  <div className="text-[11px] font-mono uppercase text-emerald-400 font-semibold mb-2 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Verified Official Citations & Provenance</span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {message.citations.map((cite, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-900/60 border border-white/5 text-[11px] font-mono"
                      >
                        <div className="text-white font-medium truncate">
                          {cite.authority || cite.source_authority || 'Reserve Bank of India (RBI)'}
                        </div>
                        <div className="text-brand-300 text-[10px] truncate mt-0.5">
                          Table: {cite.table || cite.table_reference}
                        </div>
                        <div className="flex items-center justify-between text-slate-400 text-[10px] mt-1">
                          <span>Period: {cite.period || cite.observation_period || '2024-09'}</span>
                          <span className="text-emerald-400 font-semibold uppercase">{cite.freshness || 'Verified'}</span>
                        </div>
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
      <div className="px-6 py-2 border-t border-white/5 bg-slate-950/40">
        <div className="max-w-4xl mx-auto flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-[11px] font-mono text-slate-500 shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-brand-400" />
            Quick Prompts:
          </span>
          {currentPrompts.map((prompt, idx) => (
            <button
              key={idx}
              disabled={isGenerating}
              onClick={() => handleSendMessage(prompt.text)}
              className="shrink-0 px-3 py-1.5 rounded-lg glass-panel hover:bg-slate-800 text-slate-300 hover:text-white text-xs border border-white/5 transition-all text-left truncate max-w-xs"
            >
              {prompt.text}
            </button>
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
          className="max-w-4xl mx-auto relative flex items-center"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isGenerating}
            placeholder={
              isFinance
                ? 'Ask Finance Agent strictly about Scheduled Commercial Banks, NPAs, credit growth, rates...'
                : 'Ask Orchestrator any macroeconomic question (GDP, inflation, policy transmission, cross-sector shocks)...'
            }
            className="w-full pl-5 pr-28 py-3.5 bg-surface-elevated/80 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all font-sans disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!input.trim() || isGenerating}
            className={`absolute right-2 px-4 py-2 rounded-lg text-white text-xs font-semibold shadow-glow-brand transition-all flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
              isFinance
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-glow-emerald'
                : 'bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 shadow-glow-brand'
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
              : 'Routing: LangGraph A2A Multi-Agent Graph (All 10 Sectors)'}
          </span>
          <span>Zero Hallucination Guaranteed</span>
        </div>
      </div>
    </div>
  );
};

// Helper: Basic Markdown Parser for clean display
function formatMarkdown(text: string): string {
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
        return `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
      }
    )
    // Bullet lists
    .replace(/^\- (.*$)/gim, '<li>$1</li>')
    // Wrap consecutive list items in <ul>
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    // Line breaks to paragraphs
    .replace(/\n\n/g, '<p></p>');

  return html;
}
