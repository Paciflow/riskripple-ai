from pathlib import Path

import pytest

from riskripple.tools import finance_tools as FT

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = REPO_ROOT / "data" / "fixtures" / "market"

pytestmark = pytest.mark.skipif(
    not SNAPSHOT_DIR.exists(), reason="demo data snapshot not built (run scripts/build_demo_snapshot.py)"
)


def test_tool_chain_against_real_snapshot():
    history = FT.load_price_history(["SPY", "AGG"], snapshot_dir=str(SNAPSHOT_DIR))
    assert history["n_observations"] > 0
    assert "SPY" in history["provenance"]

    returns = FT.calculate_returns(history["_panel_csv"])
    assert returns["n_observations"] == history["n_observations"] - 1

    vol = FT.calculate_volatility(returns["_returns_csv"], "SPY")
    assert vol["annualized_volatility"] > 0

    corr = FT.calculate_correlation_matrix(returns["_returns_csv"])
    assert corr["correlation_matrix"]["SPY"]["SPY"] == pytest.approx(1.0)

    dd = FT.calculate_max_drawdown(returns["_returns_csv"], "SPY")
    assert dd["max_drawdown"] <= 0

    sharpe = FT.calculate_sharpe_ratio(returns["_returns_csv"], "SPY", risk_free_rate=0.0)
    assert isinstance(sharpe["sharpe_ratio"], float)


def test_calculate_portfolio_exposure_normalizes_and_flags_largest():
    result = FT.calculate_portfolio_exposure({"SPY": 2.0, "QQQ": 2.0})
    assert result["weights"]["SPY"] == pytest.approx(0.5)
    assert result["largest_position"]["weight"] == pytest.approx(0.5)


def test_run_stress_test_tool_labels_hypothetical():
    result = FT.run_stress_test_tool(100_000, {"QQQ": 1.0}, "severe")
    assert "HYPOTHETICAL" in result["assumptions_label"]
    assert result["portfolio_pnl"] < 0


def test_run_stress_test_tool_rejects_unknown_scenario():
    with pytest.raises(ValueError):
        FT.run_stress_test_tool(100_000, {"QQQ": 1.0}, "apocalyptic")


def test_compare_allocations_against_real_snapshot():
    history = FT.load_price_history(["SPY", "QQQ", "AGG"], snapshot_dir=str(SNAPSHOT_DIR))
    returns = FT.calculate_returns(history["_panel_csv"])
    comparison = FT.compare_allocations(
        returns["_returns_csv"],
        {
            "conservative": {"AGG": 0.8, "SPY": 0.2},
            "aggressive": {"SPY": 0.5, "QQQ": 0.5},
        },
    )
    assert comparison["conservative"]["annualized_volatility"] < comparison["aggressive"]["annualized_volatility"]
