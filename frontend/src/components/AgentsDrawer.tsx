import React from 'react';
import { X, ShieldCheck, Database, Layers } from 'lucide-react';

interface AgentsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface AgentInfo {
  id: string;
  name: string;
  authority: string;
  canonicalIndicators: string[];
  mcpTools: string[];
  description: string;
  badgeColor: string;
}

const DOMAIN_AGENTS: AgentInfo[] = [
  {
    id: 'real-sector',
    name: 'Real Economy Domain Agent',
    authority: 'MoSPI (National Accounts & CSO)',
    canonicalIndicators: ['in.macro.real.gdp_growth', 'in.macro.real.iip_growth', 'in.macro.real.gfcf_investment'],
    mcpTools: ['get_national_income_snapshot', 'get_industry_snapshot'],
    description: 'Tracks constant & current GDP growth, index of industrial production, and fixed capital formation using Hodrick-Prescott trend filters.',
    badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/30'
  },
  {
    id: 'prices-sector',
    name: 'Prices & Inflation Domain Agent',
    authority: 'MoSPI & DPIIT Office of Economic Adviser',
    canonicalIndicators: ['in.macro.prices.cpi_headline', 'in.macro.prices.cpi_food', 'in.macro.prices.wpi_all', 'in.macro.prices.brent_crude'],
    mcpTools: ['get_cpi_snapshot', 'get_wpi_snapshot', 'get_crude_oil_snapshot'],
    description: 'Deconstructs food vs core inflation divergence, wholesale price index shocks, and international crude oil pass-through elasticities.',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30'
  },
  {
    id: 'monetary-sector',
    name: 'Monetary & Banking Domain Agent',
    authority: 'Reserve Bank of India (RBI DBIE)',
    canonicalIndicators: ['in.macro.monetary.repo_rate', 'in.macro.monetary.standing_deposit_facility', 'in.macro.monetary.bank_credit_growth'],
    mcpTools: ['get_repo_rate_snapshot', 'get_credit_growth_snapshot'],
    description: 'Monitors real policy rates, liquidity adjustment facility balances, and commercial bank non-food credit expansion.',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
  },
  {
    id: 'fiscal-sector',
    name: 'Fiscal Sector Domain Agent',
    authority: 'Ministry of Finance & CGA',
    canonicalIndicators: ['in.macro.fiscal.debt_to_gdp', 'in.macro.fiscal.central_capex_growth', 'in.macro.fiscal.gross_tax_growth'],
    mcpTools: ['get_debt_to_gdp_snapshot'],
    description: 'Assesses debt sustainability against FRBM glide paths, gross tax collections, and capital expenditure multipliers.',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30'
  },
  {
    id: 'external-sector',
    name: 'External Sector Domain Agent',
    authority: 'RBI & Ministry of Commerce',
    canonicalIndicators: ['in.macro.external.forex_reserves', 'in.macro.external.usd_inr_exchange_rate', 'in.macro.external.merchandise_trade_deficit'],
    mcpTools: ['get_forex_reserves_snapshot'],
    description: 'Tracks foreign exchange reserve adequacy, import cover months, current account deficit, and USD/INR volatility buffering.',
    badgeColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
  },
  {
    id: 'capital-markets',
    name: 'Capital Markets Domain Agent',
    authority: 'NSE, SEBI & AMFI',
    canonicalIndicators: ['in.macro.capmarkets.nifty_50', 'in.macro.capmarkets.india_vix', 'in.macro.capmarkets.dii_mutual_fund_flows'],
    mcpTools: ['get_equity_snapshot', 'get_vix_snapshot', 'get_mf_flows_snapshot'],
    description: 'Monitors NIFTY valuation multiples, India VIX regime classification, corporate earnings, and institutional capital flows.',
    badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/30'
  },
  {
    id: 'agri-sector',
    name: 'Agriculture & Rural Domain Agent',
    authority: 'Ministry of Agriculture & IMD',
    canonicalIndicators: ['in.macro.agri.foodgrain_production', 'in.macro.agri.minimum_support_price_growth', 'in.macro.agri.monsoon_departure'],
    mcpTools: ['get_agriculture_snapshot'],
    description: 'Analyzes spatial monsoon precipitation anomalies, seasonal crop yields, and rural wage dynamics.',
    badgeColor: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
  },
  {
    id: 'labour-sector',
    name: 'Labour & Employment Domain Agent',
    authority: 'EPFO & MoSPI PLFS',
    canonicalIndicators: ['in.macro.labour.epfo_additions', 'in.macro.labour.unemployment_rate'],
    mcpTools: ['get_epfo_payroll_snapshot'],
    description: 'Evaluates net monthly formal payroll additions, workforce formalization momentum, and urban-rural employment shifts.',
    badgeColor: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
  }
];

export const AgentsDrawer: React.FC<AgentsDrawerProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col text-slate-100 overflow-hidden">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Macroeconomic Domain Agents
              </h2>
              <p className="text-xs text-slate-400">
                8 Autonomous A2A Domain Executors with Model Context Protocol (FastMCP)
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

        {/* Drawer List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {DOMAIN_AGENTS.map((agent) => (
            <div
              key={agent.id}
              className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">{agent.name}</h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-0.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Authority: <strong className="text-slate-200">{agent.authority}</strong></span>
                  </div>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${agent.badgeColor}`}>
                  Active Agent
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {agent.description}
              </p>

              {/* Canonical Indicators */}
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                  Canonical Indicators
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {agent.canonicalIndicators.map((ind) => (
                    <span
                      key={ind}
                      className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300 font-mono text-[11px]"
                    >
                      {ind}
                    </span>
                  ))}
                </div>
              </div>

              {/* MCP Tools */}
              <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80">
                <span className="flex items-center gap-1">
                  <Database className="w-3.5 h-3.5 text-slate-500" />
                  FastMCP Tools: {agent.mcpTools.join(', ')}
                </span>
                <span className="text-slate-500">SHA-256 Provenance</span>
              </div>
            </div>
          ))}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Decoupled A2A Protocol • JSON-RPC / REST</span>
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
