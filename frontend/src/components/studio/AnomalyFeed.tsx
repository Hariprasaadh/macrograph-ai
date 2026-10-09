import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, ExternalLink } from 'lucide-react';
import { MacroAnomaly, CitationItem } from '../../types';

interface AnomalyFeedProps {
  anomalies: MacroAnomaly[];
  onInspectEvidence?: (citation: CitationItem | null | undefined, name: string, value: string, period: string) => void;
}

export const AnomalyFeed: React.FC<AnomalyFeedProps> = ({ anomalies, onInspectEvidence }) => {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="p-6 rounded-2xl glass-panel border border-white/10 text-center text-slate-400 text-xs font-mono">
        No active macro structural anomalies detected under current monitoring rules.
      </div>
    );
  }

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'positive_structural':
        return {
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
          badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          border: 'border-emerald-500/20 hover:border-emerald-500/40',
          label: 'Structural Anchor',
        };
      case 'watch':
        return {
          icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
          badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          border: 'border-amber-500/20 hover:border-amber-500/40',
          label: 'Policy Watch',
        };
      case 'critical':
        return {
          icon: <AlertCircle className="w-4 h-4 text-rose-400" />,
          badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
          border: 'border-rose-500/20 hover:border-rose-500/40',
          label: 'Elevated Risk',
        };
      default:
        return {
          icon: <Info className="w-4 h-4 text-cyan-400" />,
          badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
          border: 'border-cyan-500/20 hover:border-cyan-500/40',
          label: 'Macro Signal',
        };
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
            Macro Structural Anomaly Telemetry
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-500">{anomalies.length} Signals Active</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {anomalies.map((anom) => {
          const style = getSeverityStyle(anom.severity);
          return (
            <div
              key={anom.id}
              className={`p-4 rounded-xl bg-slate-900/60 border ${style.border} transition-all space-y-2.5 flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {style.icon}
                    <h4 className="text-xs font-semibold text-slate-200">{anom.title}</h4>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${style.badge}`}>
                    {style.label}
                  </span>
                </div>

                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{anom.description}</p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-white/5 text-[11px] font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">{anom.metric}:</span>
                  <span className="text-white font-bold">{anom.value}</span>
                  <span className="text-slate-600">({anom.period})</span>
                </div>

                {onInspectEvidence && anom.citation && (
                  <button
                    onClick={() => onInspectEvidence(anom.citation, anom.title, anom.value, anom.period)}
                    className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    <span>Audit Chain</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
