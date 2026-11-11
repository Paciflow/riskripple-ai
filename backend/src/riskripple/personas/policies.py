"""Investor persona policy engine (master spec section 11).

Personas constrain a candidate allocation; they never hardcode a single "optimal"
portfolio. Candidate allocations are generated deterministically from the constraints
and then evaluated with the same financial dataset so Prudent/Equilibre/Audacieux are
directly comparable.
"""
from __future__ import annotations

import pandas as pd

from riskripple.finance import portfolio as P, returns as R, risk as K
from riskripple.finance.stress import StressScenario, run_stress_test
from riskripple.schemas.models import PersonaConstraints, PersonaEvaluation, PersonaName

PERSONA_CONSTRAINTS: dict[PersonaName, PersonaConstraints] = {
    PersonaName.PRUDENT: PersonaConstraints(
        persona=PersonaName.PRUDENT,
        max_equity_allocation=0.35,
        max_single_asset_weight=0.15,
        max_sector_weight=0.20,
        drawdown_tolerance=-0.12,
        min_cash_or_bond_allocation=0.40,
        description="Prioritizes capital preservation, diversification, and downside protection.",
    ),
    PersonaName.EQUILIBRE: PersonaConstraints(
        persona=PersonaName.EQUILIBRE,
        max_equity_allocation=0.65,
        max_single_asset_weight=0.25,
        max_sector_weight=0.35,
        drawdown_tolerance=-0.25,
        min_cash_or_bond_allocation=0.15,
        description="Balances long-term growth with moderate risk.",
    ),
    PersonaName.AUDACIEUX: PersonaConstraints(
        persona=PersonaName.AUDACIEUX,
        max_equity_allocation=1.0,
        max_single_asset_weight=0.40,
        max_sector_weight=0.60,
        drawdown_tolerance=-0.45,
        min_cash_or_bond_allocation=0.0,
        description="Accepts greater volatility and drawdowns in pursuit of growth.",
    ),
}

# Asset classification for the demo universe (section 6.6 / 20). Real deployments
# would source this from reference data, not a hardcoded map.
ASSET_CLASS = {
    "SPY": "equity", "QQQ": "equity", "NVDA": "equity", "AMD": "equity", "INTC": "equity",
    "AGG": "bond", "BIL": "cash", "GLD": "commodity",
}
ASSET_SECTOR = {
    "SPY": "broad_market", "QQQ": "technology", "NVDA": "technology",
    "AMD": "technology", "INTC": "technology",
    "AGG": "fixed_income", "BIL": "cash", "GLD": "commodities",
}


def generate_candidate_allocation(constraints: PersonaConstraints, universe: list[str]) -> dict[str, float]:
    """Deterministic rule-based allocation generator, not a hardcoded 'optimal' portfolio.

    Splits the equity sleeve equally across available equity assets (capped at
    max_single_asset_weight each), fills the rest with bonds/cash up to the
    persona's minimum defensive allocation, and puts any remainder in the commodity
    sleeve (gold) as a diversifier.
    """
    equities = [a for a in universe if ASSET_CLASS.get(a) == "equity"]
    bonds = [a for a in universe if ASSET_CLASS.get(a) == "bond"]
    cash = [a for a in universe if ASSET_CLASS.get(a) == "cash"]
    commodities = [a for a in universe if ASSET_CLASS.get(a) == "commodity"]

    equity_budget = constraints.max_equity_allocation
    defensive_budget = max(constraints.min_cash_or_bond_allocation, 1.0 - equity_budget)
    commodity_budget = max(0.0, 1.0 - equity_budget - defensive_budget)

    weights: dict[str, float] = {}

    if equities:
        per_asset = min(equity_budget / len(equities), constraints.max_single_asset_weight)
        for a in equities:
            weights[a] = per_asset
        allocated = per_asset * len(equities)
        leftover_equity = equity_budget - allocated
    else:
        leftover_equity = 0.0

    defensive_pool = bonds + cash
    defensive_total = defensive_budget + leftover_equity
    if defensive_pool:
        per_defensive = defensive_total / len(defensive_pool)
        for a in defensive_pool:
            weights[a] = weights.get(a, 0.0) + per_defensive
    elif commodities:
        commodity_budget += defensive_total

    if commodities:
        per_commodity = commodity_budget / len(commodities)
        for a in commodities:
            weights[a] = weights.get(a, 0.0) + per_commodity

    return P.normalize_weights({k: v for k, v in weights.items() if v > 0})


def check_constraint_violations(weights: dict[str, float], constraints: PersonaConstraints, mdd: float) -> list[str]:
    violations = []
    equity_weight = sum(w for a, w in weights.items() if ASSET_CLASS.get(a) == "equity")
    if equity_weight > constraints.max_equity_allocation + 1e-6:
        violations.append(
            f"equity allocation {equity_weight:.1%} exceeds persona max of {constraints.max_equity_allocation:.1%}"
        )
    asset, max_w = P.max_single_asset_weight(weights)
    if max_w > constraints.max_single_asset_weight + 1e-6:
        violations.append(
            f"single-asset weight on {asset} ({max_w:.1%}) exceeds persona max of "
            f"{constraints.max_single_asset_weight:.1%}"
        )
    # Sector concentration is an equity-diversification check (e.g. "too much in tech
    # stocks"), not an asset-class check -- bond/cash/commodity sleeves are governed by
    # max_equity_allocation / min_cash_or_bond_allocation instead, so they're excluded
    # here to avoid double-counting the same money against two unrelated constraints.
    equity_weights = {a: w for a, w in weights.items() if ASSET_CLASS.get(a) == "equity"}
    sector_weights = P.sector_concentration(equity_weights, ASSET_SECTOR)
    for sector, w in sector_weights.items():
        if w > constraints.max_sector_weight + 1e-6:
            violations.append(
                f"equity sector concentration in {sector} ({w:.1%} of total portfolio) "
                f"exceeds persona max of {constraints.max_sector_weight:.1%}"
            )
    if mdd < constraints.drawdown_tolerance:
        violations.append(
            f"historical max drawdown ({mdd:.1%}) exceeds persona tolerance of "
            f"{constraints.drawdown_tolerance:.1%}"
        )
    return violations


def evaluate_persona(
    persona: PersonaName,
    returns_panel: pd.DataFrame,
    *,
    risk_free_rate: float = 0.0,
    scenarios: dict[str, StressScenario] | None = None,
    portfolio_value: float = 100_000.0,
) -> PersonaEvaluation:
    """Generate and evaluate a candidate allocation for one persona against real
    historical return data, plus any hypothetical stress scenarios supplied."""
    constraints = PERSONA_CONSTRAINTS[persona]
    universe = list(returns_panel.columns)
    weights = generate_candidate_allocation(constraints, universe)

    port_returns = P.portfolio_returns(returns_panel, weights)
    ann_return = R.annualized_return(port_returns)
    ann_vol = K.annualized_volatility(port_returns)
    sharpe = K.sharpe_ratio(port_returns, risk_free_rate=risk_free_rate)
    drawdown = K.max_drawdown(port_returns)
    hhi = P.herfindahl_index(weights)

    violations = check_constraint_violations(weights, constraints, drawdown.max_drawdown)

    scenario_pnl: dict[str, float] = {}
    for name, scenario in (scenarios or {}).items():
        result = run_stress_test(portfolio_value, weights, scenario)
        scenario_pnl[name] = result.portfolio_pnl

    return PersonaEvaluation(
        persona=persona,
        proposed_weights=weights,
        annualized_return=ann_return,
        annualized_volatility=ann_vol,
        sharpe_ratio=sharpe,
        max_drawdown=drawdown.max_drawdown,
        herfindahl_index=hhi,
        constraint_violations=violations,
        scenario_pnl=scenario_pnl,
    )


def compare_personas(
    personas: list[PersonaName],
    returns_panel: pd.DataFrame,
    *,
    risk_free_rate: float = 0.0,
    scenarios: dict[str, StressScenario] | None = None,
) -> list[PersonaEvaluation]:
    return [
        evaluate_persona(p, returns_panel, risk_free_rate=risk_free_rate, scenarios=scenarios)
        for p in personas
    ]
