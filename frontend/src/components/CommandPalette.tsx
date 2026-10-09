import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Layers, Activity, TrendingUp, ArrowRight } from 'lucide-react';

export interface CommandItem {
  id: string;
  title: string;
  category: 'Indicator' | 'Sector' | 'Action';
  subtitle?: string;
  badge?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSector?: (sector: string) => void;
  onTriggerSync?: () => void;
  onOpenEvidence?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectSector,
  onTriggerSync,
  onOpenEvidence,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const items: CommandItem[] = [
    {
      id: 'ind-credit',
      title: 'Non-Food Bank Credit & Sectoral Deployment',
      category: 'Indicator',
      subtitle: 'RBI DBIE r539 • ₹217.96 L Cr (+13.0% YoY)',
      badge: 'Finance',
      action: () => {
        onSelectSector?.('finance');
        onClose();
      },
    },
    {
      id: 'ind-gnpa',
      title: 'Scheduled Commercial Banks Asset Quality (Gross NPA)',
      category: 'Indicator',
      subtitle: 'RBI DBIE r330 • 2.80% (Multi-decadal low)',
      badge: 'Finance',
      action: () => {
        onSelectSector?.('finance');
        onClose();
      },
    },
    {
      id: 'ind-crar',
      title: 'Capital Adequacy Ratio (CRAR & CET-1)',
      category: 'Indicator',
      subtitle: 'SCB Solvency 16.8% (+530 bps regulatory buffer)',
      badge: 'Finance',
      action: () => {
        onSelectSector?.('finance');
        onClose();
      },
    },
    {
      id: 'ind-rates',
      title: 'Lending Rate Structure (WALR Fresh & MCLR)',
      category: 'Indicator',
      subtitle: 'RBI DBIE r531 • Fresh WALR 9.38% vs Deposit 6.51%',
      badge: 'Rates',
      action: () => {
        onSelectSector?.('finance');
        onClose();
      },
    },
    {
      id: 'ind-gst',
      title: 'Gross GST Monthly Collections',
      category: 'Indicator',
      subtitle: 'Ministry of Finance PIB • ₹2.10 L Cr (+12.4% YoY)',
      badge: 'Fiscal',
      action: () => {
        onSelectSector?.('fiscal');
        onClose();
      },
    },
    {
      id: 'ind-deficit',
      title: 'Union Fiscal Deficit Glidepath',
      category: 'Indicator',
      subtitle: 'CGA Budget • 4.9% of GDP target for FY25',
      badge: 'Fiscal',
      action: () => {
        onSelectSector?.('fiscal');
        onClose();
      },
    },
    {
      id: 'ind-core',
      title: 'Core Infrastructure Industries Output (8 Core)',
      category: 'Indicator',
      subtitle: 'MoSPI / OEA Index • Electricity, Steel, Coal',
      badge: 'Real',
      action: () => {
        onSelectSector?.('real');
        onClose();
      },
    },
    {
      id: 'ind-pmi',
      title: 'Services Sector Purchasing Managers Index (PMI)',
      category: 'Indicator',
      subtitle: 'S&P Global / HSBC India • 59.2 Expansionary',
      badge: 'Services',
      action: () => {
        onSelectSector?.('services');
        onClose();
      },
    },
    {
      id: 'sec-all',
      title: 'All Sectors Macroeconomic Telemetry Matrix',
      category: 'Sector',
      subtitle: 'Holistic multi-agent intelligence overview',
      badge: 'Macro',
      action: () => {
        onSelectSector?.('all');
        onClose();
      },
    },
    {
      id: 'act-sync',
      title: 'Sync Live Mirrors with Official RBI DBIE Stores',
      category: 'Action',
      subtitle: 'Refresh local DuckDB sector caches',
      badge: 'Sync',
      action: () => {
        onTriggerSync?.();
        onClose();
      },
    },
    {
      id: 'act-audit',
      title: 'Open Empirical Provenance & Citation Audit Table',
      category: 'Action',
      subtitle: 'Examine complete zero-hallucination attribution chain',
      badge: 'Audit',
      action: () => {
        onOpenEvidence?.();
        onClose();
      },
    },
  ];

  const filtered = items.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.subtitle?.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-md animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-2xl bg-[#070e1e] border border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[70vh] animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Box */}
        <div className="flex items-center px-4 py-3.5 border-b border-white/10 gap-3 bg-slate-900/60">
          <Search className="w-5 h-5 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search indicators, sectors, official tables, or actions… (↑ ↓ to navigate, Enter to select)"
            className="w-full bg-transparent text-white placeholder-slate-400 text-sm focus:outline-none font-sans"
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-white/5 rounded border border-white/10">
            ESC
          </kbd>
        </div>

        {/* Search Results List */}
        <div className="overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs font-mono">
              No matching indicators or actions found. Try "credit", "npa", "gst", or "sync".
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`px-3 py-2.5 rounded-xl cursor-pointer flex items-center justify-between transition-colors ${
                    isSelected ? 'bg-brand-500/15 border border-brand-500/30' : 'hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-2 rounded-lg shrink-0 ${
                        item.category === 'Indicator'
                          ? 'bg-cyan-500/10 text-cyan-400'
                          : item.category === 'Sector'
                          ? 'bg-indigo-500/10 text-indigo-400'
                          : 'bg-emerald-500/10 text-emerald-400'
                      }`}
                    >
                      {item.category === 'Indicator' ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : item.category === 'Sector' ? (
                        <Layers className="w-4 h-4" />
                      ) : (
                        <Activity className="w-4 h-4" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs sm:text-sm font-semibold text-white truncate">
                        {item.title}
                      </div>
                      {item.subtitle && (
                        <div className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">
                          {item.subtitle}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    {item.badge && (
                      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-white/5 text-slate-300 border border-white/10">
                        {item.badge}
                      </span>
                    )}
                    <ArrowRight className={`w-3.5 h-3.5 ${isSelected ? 'text-cyan-400' : 'text-slate-600'}`} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-white/5 bg-slate-950/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span>Macrograph-AI Telemetry</span>
        </div>
      </div>
    </div>
  );
};
