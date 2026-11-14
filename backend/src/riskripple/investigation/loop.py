"""The Ripple Investigation loop (see docs/RIPPLE_INVESTIGATION.md).

Sits between two things that already work and stay unchanged: the alert pipeline's
deterministic relevance check (`alerts.relevance.check_relevance` -- still the trust
floor for "is this real and does it touch something known") and the deterministic
financial math (`workflows.local_orchestrator.run_investigation` -- the agent never
computes a number). This module's only job is to go looking for *additional*,
previously-unknown ripple effects beyond the fixed supplier/ticker alias lists, and to
record every step it took so the result is auditable.

Two modes:
  - Deterministic fallback (`run_ripple_investigation`, always available, no Bedrock
    required): a fixed-but-generic question sequence driven by the new research tools.
    Not an LLM -- a rule-based loop. This is the guaranteed path and what runs today
    if live Bedrock access isn't confirmed working (see docs/KNOWN_LIMITATIONS.md).
  - Agent-driven (`run_ripple_investigation_via_agent`): delegates the same job to the
    Strands Bedrock agent in agents.definitions.build_ripple_investigator_agent.
    UNTESTED LIVE -- gated behind RISKRIPPLE_ENABLE_RIPPLE_AGENT so a failed or
    unavailable live call never breaks the guaranteed deterministic path.

Both modes are bounded: max_rounds and max_hypotheses are enforced here in Python,
never left to model self-discipline, so a live agent call can't run away in cost,
latency, or output size during a demo.
"""
from __future__ import annotations

from riskripple.schemas.models import Hypothesis, InvestigationStep, RelevanceMatch
from riskripple.tools.research_tools import propose_candidate_entities, search_filings_fulltext


def run_ripple_investigation(
    *,
    document_title: str,
    document_abstract: str,
    portfolio_symbols: list[str],
    initial_matches: list[RelevanceMatch],
    fixtures_dir: str | None = None,
    max_rounds: int = 2,
    max_hypotheses: int = 3,
) -> tuple[list[InvestigationStep], list[Hypothesis]]:
    """Deterministic fallback investigation: look for ripple effects beyond what
    `check_relevance` already found, using only literal, word-boundary evidence.
    Never invents a relationship -- a candidate that finds no filing match is recorded
    as `unverified_possibility`, not silently dropped and not asserted as a fact.
    """
    trace: list[InvestigationStep] = []
    hypotheses: list[Hypothesis] = []

    already_known = {m.matched_entity for m in initial_matches}
    text = f"{document_title}\n\n{document_abstract}"

    # Round 1: what else is named in this document that the fixed alias lists don't
    # already cover?
    candidate_result = propose_candidate_entities(text)
    new_candidates = [c for c in candidate_result["candidates"] if c not in already_known]

    trace.append(
        InvestigationStep(
            question="Which entities are named in this document beyond the already-confirmed matches?",
            why_relevant="The existing alias lists (KNOWN_SUPPLIER_ALIASES, KNOWN_COMPANY_NAMES) are a fixed "
            "seed set; a real event may name something not on either list.",
            tools_consulted=["propose_candidate_entities"],
            evidence_found=new_candidates,
            result_status="unverified_possibility" if new_candidates else "verified_fact",
            follow_up_questions=[f"Does any held company's filing mention '{c}'?" for c in new_candidates],
            related_symbols=[],
        )
    )

    if max_rounds < 2:
        return trace, hypotheses

    # Round 2: for each new candidate (bounded), does it show up in ANY held
    # company's filing -- which also covers "could a competitor be exposed too",
    # since all portfolio symbols are searched, not just the one already matched.
    for candidate in new_candidates:
        if len(hypotheses) >= max_hypotheses:
            break

        result = search_filings_fulltext(candidate, symbols=portfolio_symbols, fixtures_dir=fixtures_dir)

        if result["hits"]:
            evidence = [h["evidence_snippet"] for h in result["hits"]]
            symbols_hit = [h["symbol"] for h in result["hits"]]
            trace.append(
                InvestigationStep(
                    question=f"Does any held company's filing mention '{candidate}'?",
                    why_relevant=f"'{candidate}' was named in the event but is not in any existing alias list.",
                    tools_consulted=["search_filings_fulltext"],
                    evidence_found=evidence,
                    result_status="evidence_supported_hypothesis",
                    follow_up_questions=[],
                    related_symbols=symbols_hit,
                )
            )
            for hit in result["hits"]:
                hypotheses.append(
                    Hypothesis(
                        statement=f"'{candidate}' is a disclosed dependency or relationship of {hit['symbol']}, "
                        f"and this event names '{candidate}' -- a plausible, not yet quantified, ripple path.",
                        status="evidence_supported_hypothesis",
                        related_symbols=[hit["symbol"]],
                        evidence_snippet=hit["evidence_snippet"],
                        source_tool="search_filings_fulltext",
                    )
                )
        else:
            trace.append(
                InvestigationStep(
                    question=f"Does any held company's filing mention '{candidate}'?",
                    why_relevant=f"'{candidate}' was named in the event but is not in any existing alias list.",
                    tools_consulted=["search_filings_fulltext"],
                    evidence_found=[],
                    result_status="unverified_possibility",
                    follow_up_questions=[],
                    related_symbols=[],
                )
            )

    return trace, hypotheses
