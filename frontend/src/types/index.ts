export type SectorId =
  | 'finance_sector'
  | 'real_sector'
  | 'monetary_sector'
  | 'prices_sector'
  | 'capital_market_sector'
  | 'fiscal_sector'
  | 'external_sector'
  | 'agriculture_sector'
  | 'labour_sector'
  | 'services_sector';

export interface SectorAgent {
  id: string;
  name: string;
  sectorKey: SectorId | 'orchestrator';
  domain: string;
  authority: string;
  status: 'active' | 'staged' | 'in_development';
  ownership: string[];
  mcpSources: string[];
  icon: string;
  color: string;
  description: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatar: string;
  role: string;
  organization?: string;
}

export interface CitationItem {
  citation_id?: number;
  source_agent: string;
  source?: string;
  source_category?: string;
  indicator?: string;
  value?: number;
  authority?: string;
  source_authority?: string;
  table?: string;
  table_reference?: string;
  document_title?: string;
  retrieval_url?: string;
  dataset?: string;
  observation_period?: string;
  period?: string;
  freshness?: 'live' | 'cached' | 'unavailable' | string;
  source_base_url?: string;
  source_note?: string;
  as_of?: string;
  fetched_at?: string;
  frequency?: string;
  unit?: string;
  provenance_hash?: string;
  mcp_tool?: string;
  upstream_tool?: string;
  data_vintage?: string;
  retrieved_at?: string;
  source_filters?: Record<string, unknown>;
}

export interface StreamStep {
  step: number;
  agent?: string;
  tool?: string;
  /** Present on A2A steps; later events with the same id update the step in place. */
  request_id?: string;
  title: string;
  detail: string;
  status?: 'pending' | 'running' | 'completed' | 'partial' | 'failed';
}

export interface A2ATraceNode {
  request_id: string;
  parent_request_id: string | null;
  sender_agent: string;
  receiver_agent: string;
  task: string;
  depth: number;
  started_at: string;
  status: 'pending' | 'success' | 'partial' | 'failed';
  error_codes: string[];
  duration_ms: number | null;
}

export interface A2AErrorItem {
  agent: string;
  request_id: string;
  code: string;
  message: string;
}

export interface A2ASourceItem {
  agent: string;
  source_name: string;
  source_url?: string | null;
  dataset?: string | null;
  table?: string | null;
  reporting_period?: string | null;
}

export interface A2ASummary {
  conversation_id: string | null;
  routed_agents: string[];
  routing_method: string | null;
  status: string | null;
  errors: A2AErrorItem[];
  sources: A2ASourceItem[];
  trace: A2ATraceNode[];
}

export interface A2ADependency {
  consumer: string;
  provider: string;
  task: string;
  rationale: string;
}

export interface A2AAgentCard {
  agent_id?: string;
  name: string;
  description: string;
  version?: string;
  capabilities?: string[];
  supported_tasks?: string[];
  skills?: Array<{ id?: string; name?: string }>;
  metadata?: { sector?: string; keywords?: string[] };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agentTarget?: string;
  agentRouted?: string;
  steps?: StreamStep[];
  citations?: CitationItem[];
  observations?: Array<{
    indicator_id: string;
    value: any;
    unit: string;
    observation_period: string;
    data_status: string;
  }>;
  mermaidDiagram?: string;
  confidenceScore?: number;
  dataStatus?: 'completed' | 'partial' | 'unavailable' | 'failed' | string;
  dataFreshness?: Record<string, string>;
  a2a?: A2ASummary;
  isStreaming?: boolean;
}

export interface CreditSectoralBreakdown {
  agriculture_cr: number;
  industry_msme_cr: number;
  industry_large_cr: number;
  services_cr: number;
  personal_loans_cr: number;
  personal_housing_cr: number;
  personal_vehicle_cr: number;
}

export interface CreditGrowthData {
  period: string;
  gross_credit_cr: number;
  non_food_credit_cr: number;
  non_food_credit_yoy_pct: number;
  sectoral: CreditSectoralBreakdown;
  citation: CitationItem;
  is_real_data: boolean;
}

export interface AssetQualityData {
  period: string;
  bank_group: string;
  gross_npa_pct: number;
  net_npa_pct: number;
  gross_npa_cr: number;
  net_npa_cr: number;
  provision_coverage_ratio_pct: number;
  crar_pct: number;
  cet1_pct: number;
  citation: CitationItem;
  is_real_data: boolean;
}

export interface LendingRatesData {
  period: string;
  walr_fresh_pct: number;
  walr_outstanding_pct: number;
  mclr_1yr_median_pct: number;
  wadtdr_fresh_pct: number;
  wadtdr_outstanding_pct: number;
  citation: CitationItem;
  is_real_data: boolean;
}

export interface DepositsData {
  period: string;
  aggregate_deposits_cr: number;
  deposits_yoy_pct: number;
  demand_deposits_cr: number;
  time_deposits_cr: number;
  casa_ratio_pct: number;
  bank_credit_cr: number;
  cd_ratio_pct: number;
  citation: CitationItem;
  is_real_data: boolean;
}

export interface DashboardOverview {
  status: string;
  finance_sector: {
    credit_growth: CreditGrowthData | null;
    asset_quality: AssetQualityData | null;
    lending_rates: LendingRatesData | null;
    deposits_cd_ratio: DepositsData | null;
  };
  other_sectors_preview: Array<{
    sector: string;
    indicator: string;
    value: string;
    frequency: string;
    source: string;
    status: string;
    is_mock: boolean;
  }>;
  platform_summary: {
    active_live_sectors: string[];
    staged_sectors: string[];
    development_sectors: string[];
    total_sectors: number;
  };
}
