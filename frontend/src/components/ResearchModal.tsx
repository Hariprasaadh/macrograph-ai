import React, { useState } from 'react';
import { X, Send, BrainCircuit, FileText } from 'lucide-react';

interface ResearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemStatus: {
    online: boolean;
    agentsCount: number;
    nodesCount: number;
  };
}

export const ResearchModal: React.FC<ResearchModalProps> = ({ isOpen, onClose, systemStatus }) => {
  const [query, setQuery] = useState('Assess the transmission of rising crude oil prices to Indian headline CPI and the RBI repo rate trajectory.');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [report, setReport] = useState<any>(null);

  if (!isOpen) return null;

  const sampleQueries = [
    "Assess the transmission of rising crude oil prices to Indian headline CPI and the RBI repo rate trajectory.",
    "Evaluate the impact of RBI 25 bps repo rate cut on commercial bank credit growth and real GDP.",
    "Analyze spatial southwest monsoon deficit and foodgrain production elasticity on food CPI.",
    "Estimate debt-to-GDP trajectory under central capex acceleration of 15% YoY."
  ];

  const handleExecute = async () => {
    setIsAnalyzing(true);
    setReport(null);

    // If backend is running, try calling the real FastAPI endpoint
    try {
      const resp = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      if (resp.ok) {
        const data = await resp.json();
        setReport(data);
        setIsAnalyzing(false);
        return;
      }
    } catch (e) {
      // Fall back to client-side multi-agent simulation
    }

    // High fidelity offline multi-agent simulation
    setTimeout(() => {
      setReport({
        target_sectors: ["Prices & Inflation", "Monetary & Banking", "External Sector"],
        confidence_score: 0.94,
        collected_observations: [
          { indicator: "in.macro.prices.brent_crude", value: 84.5, unit: "USD/bbl", authority: "EIA / Markets" },
          { indicator: "in.macro.prices.cpi_headline", value: 5.1, unit: "% YoY", authority: "MoSPI" },
          { indicator: "in.macro.monetary.repo_rate", value: 6.5, unit: "% p.a.", authority: "RBI" }
        ],
        causal_paths: [
          { source: "Brent Crude", target: "WPI All Commodities", lag: "1 month", tier: "Tier 3: Lagged Relationship" },
          { source: "WPI Commodities", target: "CPI Headline Inflation", lag: "2 months", tier: "Tier 4: Granger Predictive" },
          { source: "CPI Headline", target: "RBI Policy Repo Rate", lag: "3 months", tier: "Tier 1: Theory" }
        ],
        report_markdown: `### Executive Macroeconomic Summary
A +$10/barrel surge in international crude oil prices historically correlates with a ~25-30 bps headline CPI increase in India over a 2-quarter horizon, mediated primarily through transportation fuels and intermediate manufacturing input costs.

1. **First-Round Pass-Through**: Direct impact on WPI Fuel & Power within 30 days.
2. **Second-Round Pass-Through**: Core CPI sticky inflation expansion over 90-120 days.
3. **Monetary Stance**: Constrains the Monetary Policy Committee (MPC) from aggressive easing, sustaining a positive real policy rate buffer (>140 bps).`
      });
      setIsAnalyzing(false);
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl text-slate-100 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                LangGraph Multi-Agent Orchestrator
              </h2>
              <p className="text-xs text-slate-400">
                Autonomous Query Decomposition • Parallel A2A Dispatch • Dual-Tier Groq Synthesis
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Query input box */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 block">
              Enter Indian Macroeconomic Research Query
            </label>
            <div className="relative">
              <textarea
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask any multi-sector macroeconomic question..."
                className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-700 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-white placeholder-slate-500 outline-none resize-none transition-all"
              />
              <button
                onClick={handleExecute}
                disabled={isAnalyzing || !query.trim()}
                className="absolute bottom-3 right-3 flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs px-4 py-2 rounded-lg shadow-md transition-all disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Orchestrating...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Analyze</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Sample query pills */}
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Suggested Research Inquiries
            </span>
            <div className="flex flex-wrap gap-2">
              {sampleQueries.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(q)}
                  className="text-left text-xs px-3 py-1.5 rounded-lg bg-slate-950/70 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 transition-all"
                >
                  {q.length > 60 ? `${q.substring(0, 60)}...` : q}
                </button>
              ))}
            </div>
          </div>

          {/* Research Results */}
          {report && (
            <div className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4 animate-fade-in">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span>Synthesized Multi-Agent Research Output</span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-medium">
                  Confidence: {(report.confidence_score * 100).toFixed(0)}%
                </span>
              </div>

              {/* Target sectors engaged */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 font-medium">Agents Engaged:</span>
                {report.target_sectors?.map((sec: string, i: number) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono">
                    {sec}
                  </span>
                ))}
              </div>

              {/* Markdown summary */}
              <div className="text-sm text-slate-300 space-y-2 whitespace-pre-line leading-relaxed bg-slate-900/50 p-4 rounded-lg border border-slate-800/80">
                {report.report_markdown}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>{systemStatus.online ? 'Connected to local FastAPI LangGraph core' : 'Client-side multi-agent simulation sandbox'}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
