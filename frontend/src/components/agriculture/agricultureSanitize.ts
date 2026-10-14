/**
 * Agriculture-specific user-text guard.
 *
 * The Agriculture backend returns internal validation data (verdicts,
 * confidence, retry decisions, retrieval errors) under separate keys for
 * backend logic. Those values must never be rendered as the user's answer.
 * This pure helper strips any residual internal-diagnostic lines from
 * Agriculture answer text. It is intentionally Agriculture-only: it is not
 * imported by any other sector's components.
 */

const FORBIDDEN_LINE_PATTERNS: RegExp[] = [
  /availability note\s*:/i,
  /data status\s*:/i,
  /search limitation\s*:/i,
  /tavily was searched/i,
  /could not be completed/i,
  /no verified .* mapping/i,
  /mcp server failed/i,
  /tool returned an error/i,
  /^\s*(PASS|FAIL|Verdict\s*:|Decision\s*:)/i,
];

const FORBIDDEN_TEXT_PATTERNS: RegExp[] = [
  /\bPASS\b/,
  /\bFAIL\b/,
  /\bverdict\b/i,
  /\bvalidation\b.{0,20}\b(failed|failure)\b/i,
  /\bdata\b.{0,20}\b(inadequate|unavailable)\b/i,
  /\binsufficient\b/i,
  /\bnot\b.{0,20}\bverified\b/i,
  /\bout of scope\b/i,
];

export interface AgriculturePrimaryObservation {
  value?: string;
  unit?: string;
  crop?: string;
  indicator?: string;
  geography?: string;
  period?: string;
  source_name?: string;
  source_url?: string;
  estimate_status?: string | null;
  is_fallback?: boolean;
  fallback_note?: string;
}

/** Remove residual internal-diagnostic lines; collapse blank runs. */
export function sanitizeAgricultureAnswer(text: string): string {
  if (!text) return text;
  const kept = text
    .split('\n')
    .filter((line) => !FORBIDDEN_LINE_PATTERNS.some((pattern) => pattern.test(line)));
  return kept.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

/** True when user-facing text still contains an internal verdict/diagnostic. */
export function containsInternalVerdict(text: string): boolean {
  if (!text) return false;
  return FORBIDDEN_TEXT_PATTERNS.some((pattern) => pattern.test(text));
}

/**
 * Select the renderable Agriculture answer for a query.
 *
 * Returns the backend's final natural-language `answer` verbatim (never the
 * raw validation object). The `requestKey` lets callers drop stale results:
 * only render when it matches the latest issued Agriculture query.
 */
export function selectAgricultureAnswerForQuery(args: {
  requestKey: string;
  latestRequestKey: string;
  answer?: string;
  primary?: AgriculturePrimaryObservation | null;
}): string | null {
  if (args.requestKey !== args.latestRequestKey) return null;
  if (!args.answer || !args.answer.trim()) return null;
  return sanitizeAgricultureAnswer(args.answer);
}
