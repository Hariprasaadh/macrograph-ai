import { isValidElement, type ReactNode } from 'react';

/** Minimal shape of the hast nodes react-markdown hands to component overrides. */
export interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  children?: HastNode[];
}

export type StatusTone = 'good' | 'warn' | 'bad' | 'neutral';

// Hyphen-minus plus the Unicode hyphens/minus signs that LLMs emit for negative numbers.
const MINUS_SIGNS = '\\-\\u2010\\u2011\\u2012\\u2013\\u2212';
const NUMERIC_CELL = new RegExp(
  `^[+${MINUS_SIGNS}]?\\s?(?:[₹$€£]\\s?)?\\d[\\d,]*(?:\\.\\d+)?\\s?(?:%|pp|bps|bn|cr|crore|m|k|x|ms|months?|[a-z]{0,3}/[a-z]{1,4})?$`,
  'i',
);
const NEGATIVE_START = new RegExp(`^[${MINUS_SIGNS}]`);

const STATUS_TONES: Record<string, StatusTone> = {
  live: 'good',
  verified: 'good',
  verified_historical: 'good',
  available: 'good',
  completed: 'good',
  final: 'good',
  cached: 'warn',
  upstream_snapshot: 'warn',
  partial: 'warn',
  provisional: 'warn',
  stale: 'warn',
  unavailable: 'bad',
  failed: 'bad',
  error: 'bad',
  unspecified: 'neutral',
};

export function textOf(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children);
  return '';
}

export function hastText(node: HastNode | undefined): string {
  if (!node) return '';
  if (node.type === 'text') return node.value ?? '';
  return (node.children ?? []).map(hastText).join('');
}

export function isNumericText(text: string): boolean {
  const trimmed = text.replace(/[`*_]/g, '').trim();
  return trimmed.length > 0 && trimmed.length <= 18 && NUMERIC_CELL.test(trimmed);
}

/** +1 for an explicit positive sign, -1 for an explicit negative sign, 0 otherwise. */
export function signedDirection(text: string): -1 | 0 | 1 {
  const trimmed = text.replace(/[`*_]/g, '').trim();
  if (!isNumericText(trimmed)) return 0;
  if (trimmed.startsWith('+')) return 1;
  if (NEGATIVE_START.test(trimmed)) return -1;
  return 0;
}

export function statusTone(text: string): StatusTone | null {
  const key = text.replace(/[`*]/g, '').trim().toLowerCase();
  return STATUS_TONES[key] ?? null;
}

/** Per-column numeric flags for a table: a column is numeric when most non-empty body cells are numbers. */
export function numericColumns(table: HastNode): boolean[] {
  const body = (table.children ?? []).find((child) => child.tagName === 'tbody');
  const rows = (body?.children ?? []).filter((row) => row.tagName === 'tr');
  const cellsPerRow = rows.map((row) => (row.children ?? []).filter((cell) => cell.tagName === 'td'));
  const width = Math.max(0, ...cellsPerRow.map((cells) => cells.length));
  return Array.from({ length: width }, (_unused, col) => {
    const values = cellsPerRow
      .map((cells) => hastText(cells[col]).trim())
      .filter((value) => value.length > 0 && !/^(n\/a|unavailable|-|—)$/i.test(value));
    return values.length > 0 && values.filter(isNumericText).length / values.length >= 0.6;
  });
}
