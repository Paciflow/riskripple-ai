# Agents

Built with the [Strands Agents SDK](https://strandsagents.com) (official AWS
open-source project, Apache-2.0 — verified via PyPI metadata, not assumed) and
Amazon Bedrock. Each agent is a `strands.Agent` with its own `system_prompt` and a
restricted subset of `@strands.tool`-decorated Python functions
(`backend/src/riskripple/tools/`). See `backend/src/riskripple/agents/definitions.py`
for the exact prompts.

**Not MCP.** `mcp` appears only as a transitive dependency of `strands-agents` (for
optionally connecting to external MCP tool servers); nothing here uses it. Tools are
plain Python functions — Strands derives their JSON schema from type hints and
docstrings and hands that to Bedrock's Converse API directly.

**Live status:** `bedrock:InvokeModel` is access-denied on the personal AWS account
used for development, so the LLM-driven tool-selection/orchestration loop has not
been run live. What has been verified: the `Agent` objects construct correctly and
register all their tools correctly, and every tool function works correctly on its
own (73 passing tests) and in combination (the local orchestrator runs the full
pipeline against real data without any LLM in the loop). What's unverified is
specifically the model's judgment about which tool to call when and how to narrate
the result — confirm this on the hackathon account before the demo.

## Agent 1 — Regulatory Watchdog

**Tools:** `list_new_documents`
**Role:** surface candidate regulatory events from the Federal Register BIS feed.
**Key prompt constraint:** never fabricate a document or jurisdiction not present in
tool output; set confidence low and say so when evidence is thin.

## Agent 2 — Regulatory Intelligence Investigator

**Tools:** `search_sanctions_records`, `retrieve_company_filings`,
`resolve_entity_aliases`, `summarize_event_evidence`
**Role:** build a cited, evidence-grounded summary distinguishing legal
restrictions (sanctions/export controls) from broader economic exposure.
**Key prompt constraint:** never state an entity is legally sanctioned unless
`search_sanctions_records` returned a match — industry similarity is not a match.

## Agent 3 — Exposure and Contagion Mapper

**Tools:** `resolve_company_identity`, `load_company_graph`,
`find_direct_exposure_tool`, `traverse_relationships_tool`,
`calculate_exposure_weights`
**Role:** connect a regulatory event to portfolio holdings via verified
supplier/customer relationships only.
**Key prompt constraint:** never state a relationship unless `load_company_graph`
produced it (which itself only fires on a literal keyword match in real filing
text — verified against NVIDIA/AMD/Intel 10-Ks); report "no established link"
rather than guessing.

## Agent 4 — Quantitative Risk Analyst

**Tools:** `load_price_history`, `calculate_returns`, `calculate_volatility`,
`calculate_correlation_matrix`, `calculate_max_drawdown`, `calculate_sharpe_ratio`,
`calculate_portfolio_exposure`, `run_stress_test_tool`, `compare_allocations`
**Role:** the only agent that touches numbers, and only via these tools.
**Key prompt constraint:** "You MUST use the provided tools for every numeric
calculation — never compute or estimate a financial statistic yourself." Every
stress-test result must be labeled hypothetical, never a forecast.

## Agent 5 — Persona Decision and Reporting

**Tools:** `get_persona_constraints`, `evaluate_portfolio_alternatives`,
`compare_scenario_results`, `generate_decision_explanation`,
`validate_report_citations`, `save_investigation_report`
**Role:** compare Prudent/Équilibré/Audacieux, explain tradeoffs, and produce the
final investigation report.
**Key prompt constraint:** explicitly separate historical facts, calculations,
assumptions, hypothetical scenarios, and AI interpretation; call
`validate_report_citations` and refuse any unsupported citation before saving;
never suggest executing a real trade.

## Retrieval quality

Agents 2 and 3 depend on `LocalLexicalRetriever` finding the right evidence (see
`docs/EVALUATION.md` for a 34-question benchmark against the real demo fixtures:
0.88 hit@3 at the recommended `min_score=0.15` threshold, with the specific
precision/recall tradeoffs that threshold involves spelled out there, not just
asserted).

## Orchestration

Designed around Step Functions sequencing these 5 narrow agents (see
`docs/ARCHITECTURE.md`), per the master spec's guidance to prioritize reliable tool
execution over agent count. The currently-running path
(`workflows/local_orchestrator.py`) calls each agent's tools directly in that same
sequence without a live LLM loop on top, to prove the tool chain itself works
end-to-end on real data while Bedrock access is unconfirmed.
