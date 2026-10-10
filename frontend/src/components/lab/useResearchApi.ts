import { useEffect, useState } from 'react';
import type { KgGraph } from '../../types/research';

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export async function postJson<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

let graphPromise: Promise<KgGraph> | null = null;

/** Loads the real ontology graph once and shares it between all lab tabs. */
export function useKgGraph(): { graph: KgGraph | null; error: string | null } {
  const [graph, setGraph] = useState<KgGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    if (!graphPromise) graphPromise = getJson<KgGraph>('/api/v1/research/kg/graph');
    graphPromise
      .then((g) => alive && setGraph(g))
      .catch((e: unknown) => {
        graphPromise = null;
        if (alive) setError(e instanceof Error ? e.message : 'Graph request failed');
      });
    return () => {
      alive = false;
    };
  }, []);
  return { graph, error };
}
