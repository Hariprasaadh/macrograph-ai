import React, { useEffect, useId, useState } from 'react';
import { Cpu } from 'lucide-react';

interface MermaidDiagramProps {
  code: string;
  title?: string;
}

type RenderState =
  | { status: 'loading' }
  | { status: 'ready'; svg: string }
  | { status: 'error'; message: string };

let mermaidReady: Promise<typeof import('mermaid').default> | null = null;

// mermaid is large, so it is code-split and initialised once on first use.
function loadMermaid(): Promise<typeof import('mermaid').default> {
  if (!mermaidReady) {
    mermaidReady = import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'dark',
        fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
        // Edge labels carry the relation type (e.g. [STATISTICAL_ASSOCIATION]); the default 200px wrap clips them.
        flowchart: { htmlLabels: false, curve: 'basis', wrappingWidth: 600, nodeSpacing: 40, rankSpacing: 70 },
        themeVariables: {
          background: '#020617',
          primaryColor: '#0f172a',
          primaryBorderColor: '#22d3ee',
          primaryTextColor: '#e2e8f0',
          lineColor: '#38bdf8',
          edgeLabelBackground: '#0f172a',
          fontSize: '11px',
        },
      });
      return mermaid;
    });
    mermaidReady.catch(() => {
      mermaidReady = null;
    });
  }
  return mermaidReady;
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({
  code,
  title = 'Causal Transmission Path',
}) => {
  const reactId = useId();
  const [state, setState] = useState<RenderState>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    const elementId = `mermaid-${reactId.replace(/[^a-zA-Z0-9]/g, '')}`;

    loadMermaid()
      .then((mermaid) => mermaid.render(elementId, code))
      .then(({ svg }) => {
        if (!cancelled) setState({ status: 'ready', svg });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({ status: 'error', message: err instanceof Error ? err.message : 'Diagram could not be rendered' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [code, reactId]);

  return (
    <figure className="mt-4 p-3 rounded-xl bg-slate-950 border border-white/10">
      <figcaption className="text-xs font-mono text-cyan-400 font-semibold mb-2 flex items-center gap-1.5">
        <Cpu className="w-3.5 h-3.5" />
        <span>{title}</span>
      </figcaption>

      {state.status === 'loading' && (
        <div className="skeleton h-24 rounded-lg" role="status" aria-label="Rendering causal diagram" />
      )}

      {state.status === 'ready' && (
        <div
          role="img"
          aria-label={title}
          className="overflow-x-auto [&>svg]:mx-auto [&>svg]:h-auto [&>svg]:max-w-none"
          dangerouslySetInnerHTML={{ __html: state.svg }}
        />
      )}

      {state.status === 'error' && (
        <p role="alert" className="text-[11px] font-mono text-amber-300 mb-2">
          Diagram rendering failed ({state.message}). Showing source instead.
        </p>
      )}

      <details className="mt-2 group" open={state.status === 'error'}>
        <summary className="cursor-pointer text-[11px] font-mono text-slate-500 hover:text-slate-300">
          Mermaid source
        </summary>
        <pre className="mt-2 text-[11px] font-mono text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded">
          <code>{code}</code>
        </pre>
      </details>
    </figure>
  );
};
