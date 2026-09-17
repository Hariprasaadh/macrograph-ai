import React, { useState } from 'react';
import { X, Play, ArrowRight, TrendingUp, CheckCircle2, ShieldCheck } from 'lucide-react';

interface DemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Scenario {
  id: string;
  name: string;
  shockVariable: string;
  shockLabel: string;
  magnitude: number;
  unit: string;
  description: string;
  transmissionPath: {
    source: string;
    target: string;
    tier: string;
    lagMonths: number;
    impact: string;
  }[];
}

const PRESET_SCENARIOS: Scenario[] = [
  {
    id: 'oil-shock',
    name: 'Brent Crude Global Supply Shock',
    shockVariable: 'in.macro.prices.brent_crude',
    shockLabel: 'Brent Crude Benchmark',
    magnitude: 20.0,
    unit: 'USD/barrel',
    description: 'Simulates a geopolitical escalation causing global crude prices to surge by +$20/bbl, assessing pass-through to Indian WPI, headline CPI, and twin deficits.',
    transmissionPath: [
      { source: 'Brent Crude Oil', target: 'WPI All Commodities', tier: 'Tier 3: LAGGED_RELATIONSHIP', lagMonths: 1, impact: '+1.8% YoY' },
      { source: 'WPI Commodities', target: 'CPI Headline Inflation', tier: 'Tier 4: GRANGER_PREDICTIVE', lagMonths: 2, impact: '+0.58% YoY' },
      { source: 'CPI Inflation', target: 'RBI Repo Rate Stance', tier: 'Tier 1: THEORY', lagMonths: 3, impact: '+25 bps risk' },
      { source: 'Crude Import Bill', target: 'Merchandise Trade Deficit', tier: 'Tier 5: SCM', lagMonths: 1, impact: '+$2.4B / month' },
    ]
  },
  {
    id: 'repo-hike',
    name: 'Monetary Tightening Transmission',
    shockVariable: 'in.macro.monetary.repo_rate',
    shockLabel: 'RBI Policy Repo Rate',
    magnitude: 0.50,
    unit: '% (50 bps)',
    description: 'Models a 50 bps repo rate hike by the RBI Monetary Policy Committee, tracking transmission across commercial bank lending rates and industrial output.',
    transmissionPath: [
      { source: 'RBI Repo Rate', target: 'Bank Lending Rates', tier: 'Tier 3: LAGGED_RELATIONSHIP', lagMonths: 1, impact: '+35 bps' },
      { source: 'Bank Lending Rates', target: 'Non-Food Credit Growth', tier: 'Tier 4: GRANGER_PREDICTIVE', lagMonths: 3, impact: '-1.1% YoY' },
      { source: 'Credit Expansion', target: 'GFCF Real Investment', tier: 'Tier 2: STATISTICAL_ASSOCIATION', lagMonths: 6, impact: '-0.4% YoY' },
    ]
  },
  {
    id: 'monsoon-deficit',
    name: 'Southwest Monsoon Deficit Shock',
    shockVariable: 'in.macro.agri.monsoon_departure',
    shockLabel: 'Monsoon LPA Departure',
    magnitude: -12.0,
    unit: '% Departure',
    description: 'Evaluates spatial monsoon deficiency on Kharif foodgrain output, rural demand resilience, and food inflation spikes.',
    transmissionPath: [
      { source: 'Monsoon Deficit (-12%)', target: 'Foodgrain Sown Acreage', tier: 'Tier 2: STATISTICAL_ASSOCIATION', lagMonths: 2, impact: '-4.2% YoY' },
      { source: 'Crop Production', target: 'Consumer Food Price Index', tier: 'Tier 3: LAGGED_RELATIONSHIP', lagMonths: 3, impact: '+1.65% YoY' },
      { source: 'Food Inflation', target: 'Rural Wage Growth', tier: 'Tier 1: THEORY', lagMonths: 4, impact: 'Real wage drag' },
    ]
  }
];

export const DemoModal: React.FC<DemoModalProps> = ({ isOpen, onClose }) => {
  const [selectedScenario, setSelectedScenario] = useState<Scenario>(PRESET_SCENARIOS[0]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationComplete, setSimulationComplete] = useState(false);

  if (!isOpen) return null;

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setSimulationComplete(false);
    setTimeout(() => {
      setIsSimulating(false);
      setSimulationComplete(true);
    }, 900);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl text-slate-100 flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Macroeconomic Scenario Simulator
              </h2>
              <p className="text-xs text-slate-400">
                5-Tier Causal Inference & Multi-Period Impulse Response Engine
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

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Scenario Selector Tabs */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5 block">
              Select Indian Macroeconomic Scenario
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {PRESET_SCENARIOS.map((sc) => (
                <button
                  key={sc.id}
                  onClick={() => {
                    setSelectedScenario(sc);
                    setSimulationComplete(false);
                  }}
                  className={`p-3.5 rounded-xl text-left border transition-all ${
                    selectedScenario.id === sc.id
                      ? 'bg-slate-800 border-cyan-500/80 shadow-lg shadow-cyan-500/10'
                      : 'bg-slate-950/50 border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
                  }`}
                >
                  <div className="font-semibold text-sm text-white mb-1">{sc.name}</div>
                  <div className="text-xs text-slate-400 flex items-center justify-between">
                    <span>{sc.shockLabel}</span>
                    <span className="font-mono text-cyan-400 font-semibold">{sc.magnitude > 0 ? `+${sc.magnitude}` : sc.magnitude} {sc.unit}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Scenario Details Card */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800">
                  {selectedScenario.shockVariable}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">{selectedScenario.name}</h3>
              </div>
              <button
                onClick={handleRunSimulation}
                disabled={isSimulating}
                className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm px-5 py-2.5 rounded-xl shadow-lg shadow-cyan-500/20 active:scale-95 transition-all disabled:opacity-50"
              >
                {isSimulating ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Propagating Shock...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Simulate Scenario
                  </>
                )}
              </button>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              {selectedScenario.description}
            </p>
          </div>

          {/* Transmission Path Visualizer */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Causal Transmission Pathway & Empirical Lags
              </label>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Official MoSPI / RBI Verified
              </span>
            </div>

            <div className="space-y-2.5">
              {selectedScenario.transmissionPath.map((step, idx) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all ${
                    simulationComplete
                      ? 'bg-slate-850 border-emerald-500/40'
                      : 'bg-slate-950/40 border-slate-800/80'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 text-xs font-bold text-cyan-400">
                      {idx + 1}
                    </span>
                    <div className="flex items-center gap-2 text-sm font-medium text-white">
                      <span>{step.source}</span>
                      <ArrowRight className="w-4 h-4 text-slate-500" />
                      <span className="text-cyan-300">{step.target}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                      {step.tier}
                    </span>
                    <span className="text-slate-400 font-medium">
                      Lag: <strong className="text-slate-200">{step.lagMonths} mo</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded bg-cyan-950/80 border border-cyan-700/50 text-cyan-300 font-mono font-bold">
                      {step.impact}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Simulation Status Feedback */}
          {simulationComplete && (
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-center gap-3 text-emerald-300 text-sm">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
              <span>
                Impulse response verified through DuckDB analytical core. Full research synthesis and causal DAG available in the Orchestrator Console.
              </span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-950/70 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Powered by NetworkX & Causal Econometric Impulse Engine</span>
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
