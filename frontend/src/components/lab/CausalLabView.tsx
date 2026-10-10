import React, { useState } from 'react';
import { KnowledgeGraphView } from '../KnowledgeGraphView';
import { ShockwaveTab } from './ShockwaveTab';
import { TwinTab } from './TwinTab';
import { RadarTab } from './RadarTab';
import { MpcTab } from './MpcTab';

type LabTab = 'path' | 'shockwave' | 'twin' | 'radar' | 'mpc';
const TABS: Array<{ id: LabTab; label: string }> = [
  { id: 'path', label: 'Path' },
  { id: 'shockwave', label: 'Shockwave' },
  { id: 'twin', label: 'Twin' },
  { id: 'radar', label: 'Radar' },
  { id: 'mpc', label: 'MPC' },
];

/** Tab shell around the existing KnowledgeGraphView (rendered unchanged in the Path tab). */
export const CausalLabView: React.FC = () => {
  const [tab, setTab] = useState<LabTab>('path');
  return (
    <div className="flex-1 flex flex-col min-h-0 bg-background">
      <div role="tablist" aria-label="Causal lab" className="flex items-center gap-1.5 px-6 md:px-8 pt-4 pb-2 border-b border-white/5 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold font-mono transition-all ${
              tab === t.id ? 'bg-gradient-to-r from-brand-600/30 to-cyan-600/20 text-cyan-200 border border-cyan-500/40' : 'text-slate-400 hover:text-white border border-transparent'}`}>
            {t.label}
          </button>
        ))}
        <span className="ml-auto text-[10px] font-mono text-slate-500 hidden md:block">Causal Lab · SIM and SEEDED values are labelled</span>
      </div>
      {tab === 'path' ? (
        <KnowledgeGraphView />
      ) : (
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          {tab === 'shockwave' && <ShockwaveTab />}
          {tab === 'twin' && <TwinTab />}
          {tab === 'radar' && <RadarTab />}
          {tab === 'mpc' && <MpcTab />}
        </div>
      )}
    </div>
  );
};
