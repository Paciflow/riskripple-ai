import pytest

from riskripple.finance.stress import StressScenario, run_stress_test, DEMO_SCENARIOS


def test_run_stress_test_known_pnl():
    scenario = StressScenario(
        name="test",
        description="unit test scenario",
        asset_shocks={"QQQ": -0.10, "SPY": -0.05},
    )
    result = run_stress_test(
        portfolio_value=1000.0,
        weights={"QQQ": 0.5, "SPY": 0.3, "GLD": 0.2},
        scenario=scenario,
    )
    assert result.position_pnl["QQQ"] == pytest.approx(-50.0)
    assert result.position_pnl["SPY"] == pytest.approx(-15.0)
    assert result.position_pnl["GLD"] == pytest.approx(0.0)
    assert result.portfolio_pnl == pytest.approx(-65.0)
    assert result.portfolio_value_after == pytest.approx(935.0)
    assert result.unshocked_assets == ["GLD"]


def test_run_stress_test_labels_scenario_as_hypothetical():
    scenario = DEMO_SCENARIOS["moderate"]
    assert scenario.is_hypothetical is True
    result = run_stress_test(portfolio_value=100.0, weights={"QQQ": 1.0}, scenario=scenario)
    assert "HYPOTHETICAL" in result.assumptions_label


def test_demo_scenarios_cover_mild_moderate_severe():
    assert set(DEMO_SCENARIOS.keys()) == {"mild", "moderate", "severe"}
    # Severe should be worse than moderate, which should be worse than mild, for QQQ.
    assert DEMO_SCENARIOS["severe"].asset_shocks["QQQ"] < DEMO_SCENARIOS["moderate"].asset_shocks["QQQ"]
    assert DEMO_SCENARIOS["moderate"].asset_shocks["QQQ"] < DEMO_SCENARIOS["mild"].asset_shocks["QQQ"]
