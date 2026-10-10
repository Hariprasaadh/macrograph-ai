export interface KgNode { id: string; name: string; sector: string; unit?: string }

export interface KgEdge {
  relation_id: string;
  from: string;
  to: string;
  lag_months: number;
  confidence: number;
  sign: '+' | '-';
  type: string;
  mechanism?: string;
  seeded_p?: number | null;
  evidence_class?: string;
  note?: string | null;
}

export interface KgGraph { nodes: KgNode[]; edges: KgEdge[] }

export interface TrajectoryNode {
  id: string;
  name: string;
  sector: string;
  hops: number;
  lag_months: number;
  cum_confidence: number;
  cum_multiplier: number;
  baseline: number;
  delta_peak: number;
  delta_pct_of_baseline: number | null;
  series: Array<{ t: number; value: number }>;
}

export interface TrajectoryResponse {
  shock: { id: string; magnitude: number; baseline_source: string };
  horizon_months: number;
  nodes: TrajectoryNode[];
  edges: KgEdge[];
  notes: string[];
  labels: { data: string; shape: string };
}

export interface AttributionEntry {
  path: string[];
  edges: Array<{ relation_id: string; from: string; to: string; sign: string; confidence: number; lag_months: number; note?: string | null }>;
  share: number[];
  sign_flips: number;
  weakest_link: string | null;
}

export interface CompareResponse {
  shock_variable: string;
  shock_magnitude: number;
  names: Record<string, string>;
  base: Record<string, number>;
  shocked: Record<string, number>;
  delta: Record<string, number>;
  gain_per_unit: Record<string, number>;
  lag_months: Record<string, number>;
  pct_of_baseline: Record<string, number>;
  attribution: Record<string, AttributionEntry>;
  labels: { data: string; baseline_source: string };
}

export interface AnomalyItem {
  indicator_id: string;
  name: string;
  z: number;
  period: string;
  class: 'PROPAGATING' | 'ISOLATED' | 'UNLINKED';
  propagation_score: number | null;
  culprit_path: string[];
  neighbors: Array<{ id: string; z: number; direction: string; lag_months: number }>;
  expected_propagation: Array<{ id: string; name: string; lag_months: number; confidence: number }>;
  in_graph: boolean;
  freshness: string;
  labels: { data: string };
  trust: string;
}

export interface AnomalyResponse {
  as_of: string;
  window: number;
  min_points: number;
  threshold: number;
  scanned: number;
  items: AnomalyItem[];
  skipped: Array<{ indicator_id: string; reason: string; n: number }>;
  sim_injected: string | null;
  note: string | null;
}

export interface MpcSeat {
  seat: string;
  persona: string;
  vote: 'HIKE' | 'HOLD' | 'CUT';
  rule_vote: string;
  reason: string;
  cited_indicator: string | null;
  source: 'LLM' | 'RULE_BASED';
}

export interface MpcResponse {
  meeting_label: string;
  evidence: Array<{ id: string; value: number; period: string; prior_value: number | null; freshness: string }>;
  seats: MpcSeat[];
  tally: Record<string, number>;
  decision: string;
  dissent: number;
  rule_baseline: { decision: string; tally: Record<string, number> };
  agrees_with_rule_baseline: boolean;
  labels: { data: string; llm_used: boolean };
}

export interface ConsensusAgent {
  agent_id: string;
  status: string;
  duration_ms: number | null;
  observations: number;
  usable: number;
  indicators: string[];
  sources: number;
  errors: string[];
}

export interface ConsensusPayload {
  agents: ConsensusAgent[];
  peer_calls: number;
  routing_method?: string | null;
  kg: { paths: number; scenario: boolean; coverage: number };
  scores: { agent_success: number; evidence_cover: number; kg_cover: number; consensus_quality: number; confidence_score?: number | null };
  label: string;
}

export interface ModelCardPayload {
  evidence: { live: number; sourced: number; unavailable: number; total: number };
  kg: { paths: number; max_hops: number; relations: Array<{ relation_id: string; evidence_class: string; seeded_p?: number | null }> };
  model: { name: string; kind: string; scenario?: string; constants?: Record<string, number>; formula?: { text?: string; target?: string; value?: number }; baseline?: string };
  trust: { score: number; label: string; parts: Record<string, number> };
  regime: string[];
}

export interface BriefWarning {
  title: string;
  severity: 'WATCH' | 'INFO' | 'CRITICAL';
  causal_path: string[];
  action: string;
  indicator_id?: string;
  period?: string;
}

export interface EarlyBrief {
  date: string;
  headline: string;
  executive_summary: string;
  key_drivers: Array<{ pillar: string; stance: string; takeaway: string }>;
  warnings: BriefWarning[];
  watch_today: string[];
  provenance: {
    mode?: string;
    news_status?: string;
    served_from_cache?: boolean;
    is_stale?: boolean;
    counts?: { available: number; unavailable: number };
    news_counts?: { live: number; cached: number; failed: number };
  };
  llm_model?: string;
  created_at: string;
}

export interface BriefEnvelope {
  brief: EarlyBrief | null;
  last_run_at: string | null;
  is_stale: boolean;
  served_from_cache: boolean;
}
