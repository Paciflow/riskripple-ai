"""Core domain schemas (DynamoDB entity shapes per master spec section 14).

These are the data contracts shared by the API, agents, and Step Functions workflow.
Large blobs (raw documents, reports, datasets) are referenced by S3 key, not embedded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from riskripple.schemas.provenance import SourceMetadata


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class PersonaName(str, Enum):
    PRUDENT = "prudent"
    EQUILIBRE = "equilibre"
    AUDACIEUX = "audacieux"


class Holding(BaseModel):
    symbol: str
    weight: float = Field(ge=0, le=1)
    sector: str | None = None
    currency: str = "USD"


class Portfolio(BaseModel):
    portfolio_id: str = Field(default_factory=lambda: _new_id("ptf"))
    name: str
    base_currency: str = "USD"
    total_value: float = Field(gt=0)
    holdings: list[Holding]
    is_fictional: bool = True  # per spec section 3.2: simulation only, never presented as real
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegulatoryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: _new_id("evt"))
    event_type: str
    title: str
    jurisdiction: str
    effective_date: str | None = None
    publication_date: str | None = None
    affected_entities: list[str] = Field(default_factory=list)
    affected_sectors: list[str] = Field(default_factory=list)
    source_references: list[SourceMetadata] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    processing_status: Literal["new", "investigating", "investigated"] = "new"
    is_simulated: bool = False  # True for the demo's fictional export-restriction scenario


class ExposureEdge(BaseModel):
    source: str
    target: str
    relationship_type: str  # e.g. "supplier", "customer", "etf_holding", "sector_peer"
    evidence_source: str  # human-readable citation, e.g. "NVDA 10-K (0001045810-26-000021)"
    observation_date: str | None = None
    confidence: Literal["verified", "inferred", "unknown"] = "unknown"


class ExposureGraph(BaseModel):
    event_id: str
    nodes: list[str]
    edges: list[ExposureEdge]


class ScenarioDefinition(BaseModel):
    name: str
    description: str
    asset_shocks: dict[str, float]
    is_hypothetical: bool = True


class PersonaConstraints(BaseModel):
    persona: PersonaName
    max_equity_allocation: float
    max_single_asset_weight: float
    max_sector_weight: float
    drawdown_tolerance: float  # most negative acceptable historical max drawdown, e.g. -0.25
    min_cash_or_bond_allocation: float
    description: str


class PersonaEvaluation(BaseModel):
    persona: PersonaName
    proposed_weights: dict[str, float]
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    herfindahl_index: float
    constraint_violations: list[str]
    scenario_pnl: dict[str, float]  # scenario name -> portfolio P&L


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AnalysisResult(BaseModel):
    analysis_id: str = Field(default_factory=lambda: _new_id("ana"))
    portfolio_id: str
    event_id: str | None = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    persona_evaluations: list[PersonaEvaluation] = Field(default_factory=list)
    exposure_graph: ExposureGraph | None = None
    evidence_citations: list[SourceMetadata] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_identifier: str | None = None
    calculation_version: str = "finance-engine-0.1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class InvestigationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: _new_id("rpt"))
    analysis_id: str
    investment_question: str
    event_summary: str
    facts: list[str]
    assumptions: list[str]
    hypothetical_scenarios: list[str]
    ai_interpretations: list[str]
    citations: list[SourceMetadata]
    limitations: list[str]
    next_steps: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEvent(BaseModel):
    audit_id: str = Field(default_factory=lambda: _new_id("aud"))
    analysis_id: str | None = None
    workflow_execution_id: str | None = None
    agent_name: str | None = None
    tool_name: str | None = None
    status: Literal["success", "failure"] = "success"
    duration_ms: float | None = None
    model_identifier: str | None = None
    detail: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
