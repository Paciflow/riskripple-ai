"""Agent 5 (Persona Decision and Reporting Agent) tool surface."""
from __future__ import annotations

import json
from pathlib import Path

from strands import tool

from riskripple.finance.stress import DEMO_SCENARIOS
from riskripple.personas import policies as PP
from riskripple.schemas.models import PersonaName
from riskripple.schemas.provenance import SourceMetadata

REPORTS_DIR = Path(__file__).resolve().parents[4] / "data" / "analysis" / "reports"


@tool
def get_persona_constraints(persona: str) -> dict:
    """Return the configured risk/allocation constraints for a persona
    ('prudent', 'equilibre', or 'audacieux')."""
    constraints = PP.PERSONA_CONSTRAINTS[PersonaName(persona)]
    return constraints.model_dump()


def _panel_from_csv(csv_text: str):
    import io
    import pandas as pd
    return pd.read_csv(io.StringIO(csv_text), index_col=0, parse_dates=True)


@tool
def evaluate_portfolio_alternatives(returns_panel_csv: str, personas: list[str]) -> dict:
    """Generate and evaluate a candidate allocation for each requested persona against
    the same historical return data, including all demo stress scenarios."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    results = PP.compare_personas(
        [PersonaName(p) for p in personas], returns_panel, scenarios=DEMO_SCENARIOS
    )
    return {r.persona.value: r.model_dump() for r in results}


@tool
def compare_scenario_results(evaluations: dict[str, dict]) -> dict:
    """Summarize which persona is hit hardest/softest under each hypothetical
    scenario, from the output of evaluate_portfolio_alternatives."""
    scenario_names = set()
    for ev in evaluations.values():
        scenario_names.update(ev.get("scenario_pnl", {}).keys())

    summary = {}
    for scenario in scenario_names:
        pnls = {persona: ev["scenario_pnl"][scenario] for persona, ev in evaluations.items() if scenario in ev.get("scenario_pnl", {})}
        if not pnls:
            continue
        worst = min(pnls, key=lambda p: pnls[p])
        best = max(pnls, key=lambda p: pnls[p])
        summary[scenario] = {"pnl_by_persona": pnls, "hardest_hit": worst, "least_affected": best}
    return summary


@tool
def generate_decision_explanation(evaluations: dict[str, dict], scenario_summary: dict) -> dict:
    """Deterministic, template-based explanation of why personas differ (a baseline
    that does not require an LLM call; an Agent wired to a Bedrock model may use this
    as a starting draft and refine the prose, but every number it cites must match
    this structured input exactly -- see validate_report_citations)."""
    facts, assumptions, interpretations = [], [], []

    for persona, ev in evaluations.items():
        facts.append(
            f"{persona}: historical annualized return {ev['annualized_return']:.1%}, "
            f"annualized volatility {ev['annualized_volatility']:.1%}, "
            f"max drawdown {ev['max_drawdown']:.1%} (from real historical price data)."
        )
        if ev["constraint_violations"]:
            interpretations.append(
                f"{persona}'s generated allocation violates its own policy constraints: "
                f"{'; '.join(ev['constraint_violations'])}. This reflects a limited demo "
                "asset universe, not a recommended real allocation."
            )

    for scenario, info in scenario_summary.items():
        assumptions.append(
            f"'{scenario}' scenario: hypothetical, assumption-based asset shocks, not a forecast. "
            f"Hardest hit: {info['hardest_hit']} (${info['pnl_by_persona'][info['hardest_hit']]:,.0f})."
        )

    return {"facts": facts, "assumptions": assumptions, "ai_interpretations": interpretations}


@tool
def validate_report_citations(citations: list[dict], cited_source_names: list[str]) -> dict:
    """Check that every citation referenced in generated text actually exists in the
    evidence set retrieved for this analysis. Returns which cited names are
    unsupported so the caller can refuse to publish a report with a fabricated
    citation."""
    known_names = {c.get("source_name", "") for c in citations}
    unsupported = [name for name in cited_source_names if name not in known_names]
    return {"all_citations_supported": len(unsupported) == 0, "unsupported_citations": unsupported}


@tool
def save_investigation_report(report: dict, report_id: str) -> dict:
    """Persist a finished investigation report. Writes to the local filesystem in
    development; the Lambda deployment writes to S3 via the same call shape (see
    backend/src/riskripple/storage/)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{report_id}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    return {"saved_path": str(path)}


ALL_PERSONA_TOOLS = [
    get_persona_constraints,
    evaluate_portfolio_alternatives,
    compare_scenario_results,
    generate_decision_explanation,
    validate_report_citations,
    save_investigation_report,
]
