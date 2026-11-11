"""Scenario-based stress testing. All shocks are hypothetical assumptions, never predictions."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StressScenario:
    name: str
    description: str
    asset_shocks: dict[str, float]  # e.g. {"QQQ": -0.15} = assumed -15% instantaneous shock
    is_hypothetical: bool = True  # always True; kept explicit so no caller can quietly flip it


@dataclass
class StressTestResult:
    scenario_name: str
    portfolio_value_before: float
    portfolio_pnl: float
    portfolio_value_after: float
    position_pnl: dict[str, float]
    unshocked_assets: list[str]  # assets held but with no shock assumption supplied
    assumptions_label: str = (
        "HYPOTHETICAL SCENARIO: shocks are assumptions supplied by the user or demo "
        "configuration, not a model prediction of future returns."
    )


def run_stress_test(
    portfolio_value: float,
    weights: dict[str, float],
    scenario: StressScenario,
) -> StressTestResult:
    """Delta_V = sum_i(position_value_i * assumed_shock_i).

    Assets held in the portfolio but absent from `scenario.asset_shocks` are assumed
    unshocked (0% move) and are reported explicitly in `unshocked_assets` so this
    silent default is never hidden from the caller.
    """
    position_pnl: dict[str, float] = {}
    unshocked = []
    for asset, w in weights.items():
        position_value = portfolio_value * w
        shock = scenario.asset_shocks.get(asset)
        if shock is None:
            shock = 0.0
            unshocked.append(asset)
        position_pnl[asset] = position_value * shock

    total_pnl = sum(position_pnl.values())
    return StressTestResult(
        scenario_name=scenario.name,
        portfolio_value_before=portfolio_value,
        portfolio_pnl=total_pnl,
        portfolio_value_after=portfolio_value + total_pnl,
        position_pnl=position_pnl,
        unshocked_assets=unshocked,
    )


# Starting scenarios for the semiconductor-export-restriction demo (section 20 of the
# master spec). Shock magnitudes are illustrative assumptions for the simulation, not
# calibrated forecasts, and must always be labeled as such in the UI.
DEMO_SCENARIOS = {
    "mild": StressScenario(
        name="mild",
        description="Mild: targeted restriction on a narrow chip category, limited market reaction.",
        asset_shocks={"QQQ": -0.03, "SPY": -0.01},
    ),
    "moderate": StressScenario(
        name="moderate",
        description="Moderate: broader semiconductor export restriction, tech-sector selloff.",
        asset_shocks={"QQQ": -0.08, "SPY": -0.03},
    ),
    "severe": StressScenario(
        name="severe",
        description="Severe: escalating trade restriction with retaliation, broad risk-off move.",
        asset_shocks={"QQQ": -0.18, "SPY": -0.08},
    ),
}
