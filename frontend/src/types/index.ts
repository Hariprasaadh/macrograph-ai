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

export interface TimeSeriesCreditPoint {
  period: string;
  gross_credit_cr: number;
  non_food_credit_cr: number;
  non_food_credit_yoy_pct: number;
}

export interface TimeSeriesAssetPoint {
  period: string;
  gross_npa_pct: number;
  net_npa_pct: number;
  crar_pct: number;
  pcr_pct: number;
}

export interface TimeSeriesRatesPoint {
  period: string;
  walr_fresh_pct: number;
  walr_outstanding_pct: number;
  mclr_1yr_median_pct: number;
  wadtdr_fresh_pct: number;
}

export interface TimeSeriesDepositPoint {
  period: string;
  aggregate_deposits_cr: number;
  deposits_yoy_pct: number;
  cd_ratio_pct: number;
  casa_ratio_pct: number;
}

export interface GSTHistoryPoint {
  period: string;
  gross_gst_cr: number;
  cgst_cr: number;
  sgst_cr: number;
  igst_cr: number;
  cess_cr: number;
  yoy_growth_pct: number;
  citation?: CitationItem;
}

export interface FiscalDeficitPoint {
  period: string;
  fiscal_deficit_cr: number;
  fiscal_deficit_gdp_pct: number;
  citation?: CitationItem;
}

export interface ExternalSectorData {
  latest_fx?: { period: string; usd_inr_rate: number; citation?: CitationItem } | null;
  latest_reserves?: { period: string; total_reserves_usd_mn: number; total_reserves_inr_cr?: number; citation?: CitationItem } | null;
  latest_trade?: { period: string; exports_usd_bn: number; imports_usd_bn: number; trade_deficit_usd_bn: number; citation?: CitationItem } | null;
  fx_history?: Array<{ period: string; usd_inr_rate: number; citation?: CitationItem }>;
  reserves_history?: Array<{ period: string; total_reserves_usd_mn: number; citation?: CitationItem }>;
  trade_history?: Array<{ period: string; exports_usd_bn: number; imports_usd_bn: number; trade_deficit_usd_bn: number; citation?: CitationItem }>;
}

export interface CapMarketsSectorData {
  latest_gsec?: { period: string; ten_year_gsec_yield_pct: number; citation?: CitationItem } | null;
  latest_vix?: { period: string; vix_close: number; citation?: CitationItem } | null;
  gsec_history?: Array<{ period: string; ten_year_gsec_yield_pct: number; five_year_gsec_yield_pct?: number }>;
  vix_history?: Array<{ period: string; vix_close: number }>;
}

export interface LabourSectorData {
  latest_unemp?: { period: string; unemployment_rate_pct: number; citation?: CitationItem } | null;
  latest_lfpr?: { period: string; lfpr_total_pct: number; citation?: CitationItem } | null;
  unemp_history?: Array<{ period: string; unemployment_rate_pct: number }>;
}

export interface MonetarySectorData {
  latest_rates?: { period: string; repo_rate_pct: number; reverse_repo_rate_pct?: number; citation?: CitationItem } | null;
}

export interface MacroAnomaly {
  id: string;
  severity: 'positive_structural' | 'watch' | 'info' | 'anomaly';
  title: string;
  metric: string;
  value: string;
  period: string;
  rule: string;
  description: string;
  citation?: CitationItem;
}

export interface DailyBriefing {
  headline: string;
  date: string;
  executive_summary: string;
  key_drivers: Array<{ pillar: string; stance: string; takeaway: string }>;
  upcoming_catalysts: Array<{ event: string; frequency: string; expected_date: string }>;
}

export interface ScenarioImpactItem {
  indicator_name: string;
  sector: string;
  baseline: number;
  shocked_peak: number;
  delta: number;
  confidence_band: [number, number];
  transmission_lag_months: number;
  confidence_score: number;
  mechanism_summary: string;
}

export interface ScenarioSimulationOutput {
  scenario_name: string;
  shock_variable: string;
  shock_magnitude: number;
  horizon_periods: number;
  forecasted_impacts: Record<string, ScenarioImpactItem>;
  provenance_chain: string[];
}

export interface DashboardOverview {
  status: string;
  finance_sector: {
    credit_growth: CreditGrowthData | null;
    asset_quality: AssetQualityData | null;
    lending_rates: LendingRatesData | null;
    deposits_cd_ratio: DepositsData | null;
  };
  fiscal_sector?: {
    latest_gst?: GSTHistoryPoint | null;
    latest_deficit?: FiscalDeficitPoint | null;
    latest_debt?: { period: string; general_govt_gross_debt_gdp_pct: number; citation?: CitationItem } | null;
    gst_history?: GSTHistoryPoint[];
    deficit_history?: FiscalDeficitPoint[];
    debt_history?: Array<{ period: string; general_govt_gross_debt_gdp_pct: number; citation?: CitationItem }>;
  };
  external_sector?: ExternalSectorData;
  capmarkets_sector?: CapMarketsSectorData;
  labour_sector?: LabourSectorData;
  monetary_sector?: MonetarySectorData;
  real_sector?: {
    latest_core?: {
      period: string;
      overall_ici_yoy_pct: number;
      sectoral: Record<string, number>;
      citation?: CitationItem;
    } | null;
  };
  services_sector?: {
    latest_pmi?: {
      period: string;
      headline_pmi: number;
      citation?: CitationItem;
    } | null;
  };
  timeseries?: {
    credit: TimeSeriesCreditPoint[];
    asset_quality: TimeSeriesAssetPoint[];
    lending_rates: TimeSeriesRatesPoint[];
    deposits: TimeSeriesDepositPoint[];
    gst?: GSTHistoryPoint[];
    fx?: Array<{ period: string; usd_inr_rate: number }>;
    reserves?: Array<{ period: string; total_reserves_usd_mn: number }>;
    trade?: Array<{ period: string; exports_usd_bn: number; imports_usd_bn: number; trade_deficit_usd_bn: number }>;
    gsec?: Array<{ period: string; ten_year_gsec_yield_pct: number }>;
    vix?: Array<{ period: string; vix_close: number }>;
    unemployment?: Array<{ period: string; unemployment_rate_pct: number }>;
  };
  anomalies?: MacroAnomaly[];
  daily_brief?: DailyBriefing;
  union_budget?: UnionBudgetData;
  state_finances?: StateFinancesData;
  employment_open?: EmploymentOpenData;
  economy_survey?: EconomySurveyData;
  rbi_dbie_live?: RbiDbieLiveTelemetry;
  other_sectors_preview: Array<{
    sector: string;
    indicator: string;
    value: string | null;
    sub_value?: string | null;
    period?: string | null;
    frequency: string;
    source: string;
    status: string;
    citation?: CitationItem | null;
    is_mock: boolean;
  }>;
  platform_summary: {
    active_live_sectors: string[];
    staged_sectors: string[];
    development_sectors: string[];
    total_sectors: number;
  };
}

export interface UnionMinistryAllocation {
  id: string;
  name: string;
  budgetEstimate: number;
  percentOfTotal: number;
  yoyChange: number;
  perCapita?: number;
  humanContext?: string;
}

export interface UnionBudgetData {
  summary: {
    year: string;
    totalExpenditure: number;
    totalReceipts: number;
    revenueReceipts: number;
    capitalReceipts: number;
    fiscalDeficit: number;
    fiscalDeficitPercentGDP: number;
    gdp: number;
    population: number;
    perCapitaExpenditure: number;
    perCapitaDailyExpenditure: number;
    lastUpdated?: string;
    source: string;
  };
  ministries: UnionMinistryAllocation[];
  citation?: CitationItem;
}

export interface StateGSDPItem {
  id: string;
  name: string;
  gsdp: number;
  gsdpConstant?: number;
  growthRate: number;
  perCapitaNsdp: number;
  population?: number;
}

export interface StateFinancesData {
  summary: {
    year: string;
    topGsdpState: string;
    topGsdpValue: number;
    nationalGsdpTotal: number;
    growthRange: string;
    averagePerCapita: number;
    totalStatesAndUTs: number;
    statesWithData: number;
    source: string;
  };
  states: StateGSDPItem[];
  citation?: CitationItem;
}

export interface EmploymentOpenData {
  summary: {
    year: string;
    unemploymentRate: number;
    lfpr: number;
    youthUnemployment: number;
    femaleLfpr: number;
    workforceTotal: number;
    selfEmployedPct?: number;
    source: string;
  };
  timeseries: Array<{ year: string; value: number }>;
  citation?: CitationItem;
}

export interface EconomySurveyData {
  summary: {
    year: string;
    realGDPGrowth: number;
    nominalGDP: number;
    projectedGrowthLow: number;
    projectedGrowthHigh: number;
    cpiInflation: number;
    fiscalDeficitPercentGDP: number;
    currentAccountDeficitPercentGDP: number;
    source: string;
  };
  sectors: Array<{
    id: string;
    name: string;
    currentGrowth: number;
    gvaShare: number;
  }>;
  citation?: CitationItem;
}

export interface RbiDbieSeriesPoint {
  period: string;
  value: number;
  label?: string;
  secondaryValue?: number;
}

export interface RbiDbieTableDataRow {
  period: string;
  value: number | string;
  yoy?: string;
  component?: string;
  status?: string;
}

export interface RbiDbieSectorTable {
  id: string;
  schema: string;
  table: string;
  title: string;
  theme: string;
  sector: string;
  sector_name: string;
  dbie_path: string;
  frequency: string;
  unit: string;
  latest_period: string;
  latest_value: number;
  yoy_change: string;
  rows_count: number;
  series: RbiDbieSeriesPoint[];
  table_data?: RbiDbieTableDataRow[];
  citation: string;
  mcp_command?: string;
}

export interface RbiDbieTheme {
  key: string;
  label: string;
  sector: string;
  desc: string;
}

export interface RbiDbieTable {
  schema?: string;
  table?: string;
  title?: string;
  dbie_path?: string;
  frequency?: string;
  row_count?: number;
  source?: string;
  sector?: string;
  sector_name?: string;
  unit?: string;
  latest_period?: string;
  latest_value?: number;
  yoy_change?: string;
  series?: RbiDbieSeriesPoint[];
  table_data?: RbiDbieTableDataRow[];
  citation?: string;
  mcp_command?: string;
}

export interface RbiDbieMoneySupplyPoint {
  period: string;
  m3_lakh_cr: number;
  currency_lakh_cr: number;
}

export interface RbiDbieLiveTelemetry {
  m3_series: RbiDbieMoneySupplyPoint[];
  tables_catalog: RbiDbieTable[];
  sector_tables?: Record<string, RbiDbieSectorTable[]>;
  themes?: RbiDbieTheme[];
  citation?: CitationItem;
}




