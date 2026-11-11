// Mirrors backend/src/riskripple/schemas/models.py. Kept hand-written and in sync
// rather than code-generated, since the schema surface is small and stable.

export interface SourceMetadata {
  source_name: string
  source_url: string
  retrieved_at: string
  observation_date: string | null
  publication_date: string | null
  currency: string | null
  data_version: string
  content_hash: string
  license_or_restriction: string
}

export interface ExposureEdge {
  source: string
  target: string
  relationship_type: string
  evidence_source: string
  observation_date: string | null
  confidence: 'verified' | 'inferred' | 'unknown'
}

export interface ExposureGraph {
  event_id: string
  nodes: string[]
  edges: ExposureEdge[]
}

export type PersonaName = 'prudent' | 'equilibre' | 'audacieux'

export interface PersonaEvaluation {
  persona: PersonaName
  proposed_weights: Record<string, number>
  annualized_return: number
  annualized_volatility: number
  sharpe_ratio: number
  max_drawdown: number
  herfindahl_index: number
  constraint_violations: string[]
  scenario_pnl: Record<string, number>
}

export interface AnalysisResult {
  analysis_id: string
  portfolio_id: string
  event_id: string | null
  status: 'pending' | 'running' | 'complete' | 'failed'
  persona_evaluations: PersonaEvaluation[]
  exposure_graph: ExposureGraph | null
  evidence_citations: SourceMetadata[]
  assumptions: string[]
  limitations: string[]
  model_identifier: string | null
  calculation_version: string
  created_at: string
  completed_at: string | null
}

export interface InvestigationReport {
  report_id: string
  analysis_id: string
  investment_question: string
  event_summary: string
  facts: string[]
  assumptions: string[]
  hypothetical_scenarios: string[]
  ai_interpretations: string[]
  citations: SourceMetadata[]
  limitations: string[]
  next_steps: string[]
  created_at: string
}

export interface HeldPortfolioMetrics {
  weights: Record<string, number>
  annualized_return: number
  annualized_volatility: number
  sharpe_ratio: number
  max_drawdown: number
}

export interface DemoAnalysisPayload {
  analysis: AnalysisResult
  report: InvestigationReport
  held_portfolio: HeldPortfolioMetrics
  correlation_matrix: Record<string, Record<string, number>>
}

export const PERSONA_LABELS: Record<PersonaName, string> = {
  prudent: 'Prudent',
  equilibre: 'Équilibré',
  audacieux: 'Audacieux',
}

export const DEMO_PORTFOLIO_WEIGHTS: Record<string, number> = {
  SPY: 0.3, QQQ: 0.2, NVDA: 0.2, AMD: 0.1, INTC: 0.1, AGG: 0.05, GLD: 0.05,
}

export const DEMO_PORTFOLIO_VALUE = 100_000
