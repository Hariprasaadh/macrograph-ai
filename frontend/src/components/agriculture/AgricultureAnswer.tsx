import React, { useMemo } from 'react';
import {
  AgriculturePrimaryObservation,
  sanitizeAgricultureAnswer,
  selectAgricultureAnswerForQuery,
} from './agricultureSanitize';

interface AgricultureAnswerProps {
  /** Backend's final natural-language answer (public field, not validation output). */
  answer?: string;
  /** Single selected observation supporting the answer. */
  primary?: AgriculturePrimaryObservation | null;
  /** Source citations attached to the selected observation. */
  citations?: Array<{ source_url?: string; retrieval_url?: string }>;
  /** Key of the query that produced this result (stale-query guard). */
  requestKey: string;
  /** Key of the latest issued Agriculture query. */
  latestRequestKey: string;
}

/**
 * Agriculture-specific answer renderer.
 *
 * Renders exactly one primary observation: the final answer sentence, its
 * value/unit/period/scope, estimate status where relevant, and the direct
 * source link belonging to the selected observation. Internal validation
 * objects, verdicts, and raw retrieval payloads are never rendered.
 *
 * NOTE (scope): this component is intentionally not wired into the shared
 * chat workspace. Connecting it requires a one-line Agriculture-gated hook
 * at the shared chat render site (render <AgricultureAnswer> instead of raw
 * markdown when the routed agent is `agriculture_sector`). That shared file
 * was left untouched per the Agriculture-only scope restriction.
 */
export const AgricultureAnswer: React.FC<AgricultureAnswerProps> = ({
  answer,
  primary,
  citations = [],
  requestKey,
  latestRequestKey,
}) => {
  const text = useMemo(
    () =>
      selectAgricultureAnswerForQuery({
        requestKey,
        latestRequestKey,
        answer,
        primary: primary ?? null,
      }),
    [requestKey, latestRequestKey, answer, primary],
  );

  if (text === null) return null;

  const sourceUrl = primary?.source_url;
  const cited = sourceUrl && citations.some((citation) => citation.source_url === sourceUrl || citation.retrieval_url === sourceUrl);

  return (
    <div className="space-y-3" data-testid="agriculture-answer">
      <p className="text-sm leading-relaxed text-slate-100">{text}</p>
      {primary && primary.value && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-300" data-testid="agriculture-primary">
          <dt className="text-slate-500">Metric</dt>
          <dd>
            {primary.indicator} — {primary.value} {primary.unit}
          </dd>
          {primary.crop && (
            <>
              <dt className="text-slate-500">Crop</dt>
              <dd>{primary.crop}</dd>
            </>
          )}
          {primary.geography && (
            <>
              <dt className="text-slate-500">Geography</dt>
              <dd>{primary.geography}</dd>
            </>
          )}
          {primary.period && (
            <>
              <dt className="text-slate-500">Reporting period</dt>
              <dd>{primary.period}</dd>
            </>
          )}
          {primary.estimate_status && (
            <>
              <dt className="text-slate-500">Estimate</dt>
              <dd>{primary.estimate_status}</dd>
            </>
          )}
          {primary.is_fallback && primary.fallback_note && (
            <>
              <dt className="text-slate-500">Note</dt>
              <dd>{primary.fallback_note}</dd>
            </>
          )}
        </dl>
      )}
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-emerald-300 underline"
          data-testid="agriculture-source-link"
          data-cited={cited ? 'true' : 'false'}
        >
          {primary?.source_name || 'Source'}
        </a>
      )}
    </div>
  );
};

export default AgricultureAnswer;
