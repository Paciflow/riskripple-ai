import pandas as pd
import pytest

from riskripple.finance import portfolio as P


def test_portfolio_returns_weighted_sum():
    panel = pd.DataFrame(
        {"A": [0.10, -0.10], "B": [0.00, 0.20]},
        index=pd.date_range("2024-01-01", periods=2, freq="D"),
    )
    pr = P.portfolio_returns(panel, {"A": 0.5, "B": 0.5})
    assert pr.iloc[0] == pytest.approx(0.05)
    assert pr.iloc[1] == pytest.approx(0.05)


def test_portfolio_returns_rejects_unknown_asset():
    panel = pd.DataFrame({"A": [0.01]}, index=pd.date_range("2024-01-01", periods=1))
    with pytest.raises(ValueError):
        P.portfolio_returns(panel, {"Z": 1.0})


def test_portfolio_volatility_uncorrelated_assets():
    cov = pd.DataFrame(
        {"A": [0.04, 0.0], "B": [0.0, 0.09]},
        index=["A", "B"],
    )
    vol = P.portfolio_volatility({"A": 0.5, "B": 0.5}, cov)
    # variance = 0.25*0.04 + 0.25*0.09 + 0 cross term = 0.0325
    assert vol == pytest.approx(0.0325 ** 0.5)


def test_herfindahl_index():
    hhi = P.herfindahl_index({"A": 0.5, "B": 0.3, "C": 0.2})
    assert hhi == pytest.approx(0.25 + 0.09 + 0.04)


def test_herfindahl_index_single_asset_is_one():
    assert P.herfindahl_index({"A": 1.0}) == pytest.approx(1.0)


def test_max_single_asset_weight():
    asset, w = P.max_single_asset_weight({"A": 0.5, "B": 0.3, "C": 0.2})
    assert asset == "A"
    assert w == pytest.approx(0.5)


def test_sector_concentration_buckets_unknown():
    weights = {"AAPL": 0.4, "GLD": 0.2, "MYSTERY": 0.4}
    sectors = {"AAPL": "technology", "GLD": "commodities"}
    result = P.sector_concentration(weights, sectors)
    assert result["technology"] == pytest.approx(0.4)
    assert result["commodities"] == pytest.approx(0.2)
    assert result["unknown"] == pytest.approx(0.4)


def test_normalize_weights_sums_to_one():
    normalized = P.normalize_weights({"A": 2.0, "B": 2.0})
    assert sum(normalized.values()) == pytest.approx(1.0)
    assert normalized["A"] == pytest.approx(0.5)


def test_normalize_weights_rejects_nonpositive_total():
    with pytest.raises(ValueError):
        P.normalize_weights({"A": 0.0, "B": 0.0})
