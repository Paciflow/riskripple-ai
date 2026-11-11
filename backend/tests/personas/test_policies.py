import numpy as np
import pandas as pd
import pytest

from riskripple.finance.stress import DEMO_SCENARIOS
from riskripple.personas import policies as P
from riskripple.schemas.models import PersonaName


def _synthetic_returns_panel(n=300, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    # Equities more volatile than bonds/cash, gold roughly uncorrelated -- enough
    # structure to make persona differences meaningful without needing live data.
    data = {
        "SPY": rng.normal(0.0004, 0.010, n),
        "QQQ": rng.normal(0.0005, 0.014, n),
        "NVDA": rng.normal(0.0008, 0.030, n),
        "AMD": rng.normal(0.0006, 0.028, n),
        "INTC": rng.normal(0.0001, 0.022, n),
        "AGG": rng.normal(0.0001, 0.003, n),
        "BIL": rng.normal(0.00015, 0.0002, n),
        "GLD": rng.normal(0.0002, 0.009, n),
    }
    return pd.DataFrame(data, index=idx)


def test_generate_candidate_allocation_respects_equity_cap():
    constraints = P.PERSONA_CONSTRAINTS[PersonaName.PRUDENT]
    weights = P.generate_candidate_allocation(constraints, list(P.ASSET_CLASS.keys()))
    equity_weight = sum(w for a, w in weights.items() if P.ASSET_CLASS.get(a) == "equity")
    assert equity_weight <= constraints.max_equity_allocation + 1e-6
    assert sum(weights.values()) == pytest.approx(1.0)


def test_prudent_holds_less_equity_than_audacieux():
    universe = list(P.ASSET_CLASS.keys())
    prudent_w = P.generate_candidate_allocation(P.PERSONA_CONSTRAINTS[PersonaName.PRUDENT], universe)
    audacieux_w = P.generate_candidate_allocation(P.PERSONA_CONSTRAINTS[PersonaName.AUDACIEUX], universe)
    prudent_equity = sum(w for a, w in prudent_w.items() if P.ASSET_CLASS.get(a) == "equity")
    audacieux_equity = sum(w for a, w in audacieux_w.items() if P.ASSET_CLASS.get(a) == "equity")
    assert prudent_equity < audacieux_equity


def test_check_constraint_violations_flags_oversized_single_asset():
    constraints = P.PERSONA_CONSTRAINTS[PersonaName.PRUDENT]
    weights = {"NVDA": 0.9, "BIL": 0.1}
    violations = P.check_constraint_violations(weights, constraints, mdd=-0.05)
    assert any("single-asset" in v for v in violations)
    assert any("equity allocation" in v for v in violations)


def test_evaluate_persona_runs_on_synthetic_panel_and_differs_by_persona():
    panel = _synthetic_returns_panel()
    scenarios = {"severe": DEMO_SCENARIOS["severe"]}
    prudent = P.evaluate_persona(PersonaName.PRUDENT, panel, scenarios=scenarios)
    audacieux = P.evaluate_persona(PersonaName.AUDACIEUX, panel, scenarios=scenarios)

    assert prudent.annualized_volatility < audacieux.annualized_volatility
    # More tech-heavy audacieux portfolio should take a bigger hit in the severe scenario.
    assert audacieux.scenario_pnl["severe"] < prudent.scenario_pnl["severe"]


def test_compare_personas_returns_all_three():
    panel = _synthetic_returns_panel()
    results = P.compare_personas(list(PersonaName), panel)
    assert {r.persona for r in results} == set(PersonaName)
