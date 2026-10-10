import React from 'react';
import type { KgGraph } from '../../types/research';
import { KG_VIEWBOX, SECTOR_COLORS, nodePosition } from './kgLayout';

export interface EdgeStyle {
  color?: string;
  width?: number;
  dim?: boolean;
}

interface AnimatedKgSvgProps {
  graph: KgGraph;
  /** node id -> month it is reached; omitted ids are always shown as active. */
  arrival?: Record<string, number>;
  activeTime?: number | null;
  /** node id -> 0..1 glow strength (unit-free). */
  intensity?: Record<string, number>;
  /** nodes that exist in the current result; others are drawn faint. */
  involved?: Set<string>;
  pulse?: Set<string>;
  edgeStyle?: Record<string, EdgeStyle>;
  selectedId?: string | null;
  onSelectNode?: (id: string) => void;
}

const short = (name: string) => (name.length > 22 ? `${name.slice(0, 21)}…` : name);

export const AnimatedKgSvg: React.FC<AnimatedKgSvgProps> = ({
  graph, arrival, activeTime = null, intensity, involved, pulse, edgeStyle, selectedId, onSelectNode,
}) => {
  const pos = new Map(graph.nodes.map((n, i) => [n.id, nodePosition(n.id, i)]));
  const isActive = (id: string) =>
    activeTime === null || !arrival || arrival[id] === undefined ? true : arrival[id] <= activeTime;
  const isInvolved = (id: string) => (involved ? involved.has(id) : true);

  return (
    <svg viewBox={`0 0 ${KG_VIEWBOX.width} ${KG_VIEWBOX.height}`} className="w-full h-auto" role="img" aria-label="Causal knowledge graph">
      <defs>
        <marker id="kg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="#64748b" />
        </marker>
      </defs>

      {graph.edges.map((e) => {
        const a = pos.get(e.from);
        const b = pos.get(e.to);
        if (!a || !b) return null;
        const style = edgeStyle?.[e.relation_id] ?? {};
        const fired = isActive(e.from) && isActive(e.to) && isInvolved(e.from) && isInvolved(e.to);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const x1 = a.x + (dx / len) * 34;
        const y1 = a.y + (dy / len) * 22;
        const x2 = b.x - (dx / len) * 34;
        const y2 = b.y - (dy / len) * 22;
        const color = style.color ?? (fired ? (e.sign === '-' ? '#fb7185' : '#22d3ee') : '#334155');
        return (
          <g key={e.relation_id} opacity={style.dim ? 0.25 : fired ? 1 : 0.45}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color}
              strokeWidth={style.width ?? 1 + e.confidence * 2.5} markerEnd="url(#kg-arrow)" />
            <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 5} textAnchor="middle" fontSize="9" fill="#94a3b8" fontFamily="monospace">
              {e.sign}{e.lag_months}M{e.note ? ' ⚠' : ''}
            </text>
          </g>
        );
      })}

      {graph.nodes.map((n, i) => {
        const p = pos.get(n.id) ?? nodePosition(n.id, i);
        const active = isActive(n.id) && isInvolved(n.id);
        const color = SECTOR_COLORS[n.sector] ?? '#94a3b8';
        const glow = active ? (intensity?.[n.id] ?? 1) : 0;
        const selected = selectedId === n.id;
        return (
          <g key={n.id} transform={`translate(${p.x},${p.y})`} onClick={() => onSelectNode?.(n.id)}
            style={{ cursor: onSelectNode ? 'pointer' : 'default' }} opacity={isInvolved(n.id) ? 1 : 0.35}>
            {pulse?.has(n.id) && <circle r="30" fill="none" stroke="#fb7185" strokeWidth="2"><animate attributeName="r" values="26;40;26" dur="1.6s" repeatCount="indefinite" /><animate attributeName="opacity" values="0.9;0;0.9" dur="1.6s" repeatCount="indefinite" /></circle>}
            {active && <rect x="-34" y="-20" width="68" height="40" rx="12" fill={color} opacity={0.12 + 0.28 * glow} />}
            <rect x="-34" y="-20" width="68" height="40" rx="12" fill="#0b1220"
              stroke={selected ? '#ffffff' : active ? color : '#334155'} strokeWidth={selected ? 2.5 : 1.5} fillOpacity={0.85} />
            <text textAnchor="middle" y="4" fontSize="9" fill={active ? '#e2e8f0' : '#64748b'} fontFamily="ui-sans-serif, system-ui">
              {short(n.name).split(' ').reduce<string[]>((lines, word) => {
                const last = lines[lines.length - 1];
                if (last !== undefined && (last + ' ' + word).length <= 11) lines[lines.length - 1] = `${last} ${word}`;
                else lines.push(word);
                return lines;
              }, []).slice(0, 2).map((line, idx, arr) => (
                <tspan key={idx} x="0" dy={idx === 0 ? (arr.length === 1 ? 0 : -5) : 11}>{line}</tspan>
              ))}
            </text>
          </g>
        );
      })}
    </svg>
  );
};
