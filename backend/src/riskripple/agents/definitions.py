"""Strands Agent assembly for all 5 agent responsibilities (master spec section 9).

UNTESTED LIVE: invoking these agents requires bedrock:InvokeModel, which is
access-denied on the personal AWS account used for development (see
docs/KNOWN_LIMITATIONS.md). The tool functions each agent wires in are fully tested
independently (see backend/tests/tools/); what is NOT yet verified is the LLM's tool
selection and conversational orchestration on top of them. Before the hackathon demo,
run scripts/verify_bedrock_agent.py against the temporary AWS account to confirm
BEDROCK_MODEL_ID is enabled in the account's region, then smoke-test each agent once.
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from riskripple.tools.exposure_tools import ALL_EXPOSURE_TOOLS
from riskripple.tools.finance_tools import ALL_FINANCE_TOOLS
from riskripple.tools.persona_tools import ALL_PERSONA_TOOLS
from riskripple.tools.regulatory_tools import ALL_REGULATORY_TOOLS

# Not assumed to be enabled in any given account/region -- verify with
# `aws bedrock list-foundation-models` on the hackathon account before the demo, per
# the master spec's instruction not to assume access to a specific model.
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-2")


def _bedrock_model() -> BedrockModel:
    return BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_REGION)


REGULATORY_WATCHDOG_PROMPT = """You are the Regulatory Watchdog agent for RiskRipple AI.
Your job is to detect new or changed regulatory/geopolitical events relevant to the
investment universe. Use list_new_documents to find candidate publications, then use
create-event-style structured output (title, jurisdiction, affected entities/sectors,
source references, confidence) for each one. Never fabricate a document or a
jurisdiction that isn't in the tool output. If evidence is thin, set confidence low
and say so explicitly rather than overstating certainty."""

REGULATORY_INVESTIGATOR_PROMPT = """You are the Regulatory Intelligence Investigator
agent for RiskRipple AI. Given a regulatory event, use search_sanctions_records,
retrieve_company_filings, resolve_entity_aliases, and summarize_event_evidence to
build a cited, evidence-grounded summary. Distinguish legal/regulatory restrictions
(sanctions, export controls) from broader economic/market exposure. Never state that
an entity is legally sanctioned unless search_sanctions_records returned a match for
it -- a thematic or industry similarity is not a sanctions match. State uncertainty
explicitly when evidence is thin or absent."""

EXPOSURE_MAPPER_PROMPT = """You are the Exposure and Contagion Mapper agent for
RiskRipple AI. Use resolve_company_identity, load_company_graph,
find_direct_exposure_tool, traverse_relationships_tool, and calculate_exposure_weights
to connect a regulatory event to portfolio holdings via verified relationships only.
Never state a relationship exists unless it came from load_company_graph's output,
which only includes relationships with literal textual evidence. Report "no
established link" rather than guessing when a holding isn't connected to the event
within the traversal depth searched."""

QUANT_ANALYST_PROMPT = """You are the Quantitative Risk Analyst agent for RiskRipple
AI. You MUST use the provided tools (load_price_history, calculate_returns,
calculate_volatility, calculate_correlation_matrix, calculate_max_drawdown,
calculate_sharpe_ratio, calculate_portfolio_exposure, run_stress_test_tool,
compare_allocations) for every numeric calculation -- never compute or estimate a
financial statistic yourself. Always state the data source, observation date range,
and currency alongside any figure you report. Label every stress-test result as a
hypothetical assumption, never as a forecast."""

PERSONA_REPORTING_PROMPT = """You are the Persona Decision and Reporting agent for
RiskRipple AI. Use get_persona_constraints, evaluate_portfolio_alternatives,
compare_scenario_results, and generate_decision_explanation to compare investor
personas (Prudent, Equilibre, Audacieux) on the same historical data and hypothetical
scenarios. Clearly separate historical facts, quantitative calculations, modeling
assumptions, hypothetical scenarios, and your own interpretation. Before finishing,
call validate_report_citations and refuse to include any citation it flags as
unsupported. Call save_investigation_report only once the report is complete. Never
suggest executing a real trade."""


def build_regulatory_watchdog_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_REGULATORY_TOOLS[:1], system_prompt=REGULATORY_WATCHDOG_PROMPT)


def build_regulatory_investigator_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_REGULATORY_TOOLS, system_prompt=REGULATORY_INVESTIGATOR_PROMPT)


def build_exposure_mapper_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_EXPOSURE_TOOLS, system_prompt=EXPOSURE_MAPPER_PROMPT)


def build_quant_analyst_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_FINANCE_TOOLS, system_prompt=QUANT_ANALYST_PROMPT)


def build_persona_reporting_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_PERSONA_TOOLS, system_prompt=PERSONA_REPORTING_PROMPT)
