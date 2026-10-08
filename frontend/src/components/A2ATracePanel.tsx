import React, { useMemo } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, GitBranch, XCircle } from 'lucide-react';
import { A2ASummary, A2ATraceNode } from '../types';

const TASK_LABELS: Record<string, string> = {
  sector_analysis: 'sector analysis',
  repo_rate: 'repo rate',
  cpi_headline: 'headline CPI',
  bank_credit_growth: 'bank credit growth',
};

const METHOD_LABELS: Record<string, string> = {
  lexical: 'Agent Card match',
  llm: 'LLM fallback',
  default: 'Default agents',
};

interface TreeNode extends A2ATraceNode {
  children: TreeNode[];
}

function buildTree(nodes: A2ATraceNode[]): TreeNode[] {
  const byId = new Map<string, TreeNode>();
  nodes.forEach((n) => byId.set(n.request_id, { ...n, children: [] }));
  const roots: TreeNode[] = [];
  byId.forEach((node) => {
    const parent = node.parent_request_id ? byId.get(node.parent_request_id) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  return roots;
}

const STATUS_STYLES: Record<A2ATraceNode['status'], { icon: React.ReactNode; text: string; label: string }> = {
  success: { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />, text: 'text-emerald-300', label: 'ok' },
  partial: { icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />, text: 'text-amber-300', label: 'partial' },
  failed: { icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />, text: 'text-rose-300', label: 'failed' },
  pending: { icon: <CircleDashed className="w-3.5 h-3.5 text-slate-400" />, text: 'text-slate-400', label: 'pending' },
};

const TraceRow: React.FC<{ node: TreeNode }> = ({ node }) => {
  const style = STATUS_STYLES[node.status] ?? STATUS_STYLES.pending;
  return (
    <li>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 py-1">
        {style.icon}
        <span className="text-slate-200">{node.sender_agent}</span>
        <ArrowRight className="w-3 h-3 text-slate-500" aria-label="requested from" />
        <span className="text-cyan-300">{node.receiver_agent}</span>
        <span className="text-slate-500">{TASK_LABELS[node.task] ?? node.task}</span>
        <span className={`${style.text} uppercase`}>{style.label}</span>
        {node.duration_ms !== null && (
          <span className="text-slate-500">{(node.duration_ms / 1000).toFixed(1)}s</span>
        )}
        {node.error_codes.length > 0 && <span className="text-rose-300">{node.error_codes.join(', ')}</span>}
      </div>
      {node.children.length > 0 && (
        <ul className="ml-4 pl-3 border-l border-white/10">
          {node.children.map((child) => (
            <TraceRow key={child.request_id} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
};

export const A2ATracePanel: React.FC<{ a2a: A2ASummary }> = ({ a2a }) => {
  const tree = useMemo(() => buildTree(a2a.trace), [a2a.trace]);
  const peerCalls = a2a.trace.filter((n) => n.sender_agent !== 'orchestrator').length;
  const hasContent = a2a.routed_agents.length > 0 || a2a.trace.length > 0 || a2a.errors.length > 0;
  if (!hasContent) return null;

  return (
    <section aria-label="Agent-to-agent activity" className="mt-4 p-3 rounded-xl bg-slate-950 border border-white/10">
      <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
        <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
        <span className="text-indigo-300 font-semibold">A2A delegation</span>
        {a2a.routing_method && (
          <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400">
            routed by {METHOD_LABELS[a2a.routing_method] ?? a2a.routing_method}
          </span>
        )}
        <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400">
          {a2a.routed_agents.length} agent{a2a.routed_agents.length === 1 ? '' : 's'}
        </span>
        {peerCalls > 0 && (
          <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400">
            {peerCalls} sector-to-sector request{peerCalls === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {tree.length > 0 && (
        <ul className="mt-2 text-[11px] font-mono" aria-label="Request tree">
          {tree.map((node) => (
            <TraceRow key={node.request_id} node={node} />
          ))}
        </ul>
      )}

      {a2a.errors.length > 0 && (
        <div role="alert" className="mt-2 p-2 rounded-lg bg-rose-500/5 border border-rose-500/20 text-[11px] font-mono">
          <div className="text-rose-300 font-semibold mb-1">Data unavailable from these agents</div>
          <ul className="space-y-0.5 text-slate-300">
            {a2a.errors.map((err) => (
              <li key={`${err.request_id}-${err.code}`}>
                <span className="text-rose-300">{err.agent}</span> {err.code}: {err.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {a2a.conversation_id && (
        <div className="mt-2 text-[10px] font-mono text-slate-500 break-all">
          conversation {a2a.conversation_id}
        </div>
      )}
    </section>
  );
};
