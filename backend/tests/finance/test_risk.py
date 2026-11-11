import pandas as pd
import pytest

from riskripple.finance import risk as K


def _series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_annualized_volatility_exact():
    # returns [0.10, -0.10]: sample std (ddof=1) = sqrt(0.02), annualized with
    # periods_per_year=2 gives sqrt(0.02)*sqrt(2) = sqrt(0.04) = 0.2 exactly.
    r = _series([0.10, -0.10])
    vol = K.annualized_volatility(r, periods_per_year=2)
    assert vol == pytest.approx(0.2)


def test_annualized_volatility_requires_two_observations():
    with pytest.raises(ValueError):
        K.annualized_volatility(_series([0.05]))


def test_max_drawdown_known_path():
    # Prices 100 -> 120 -> 90 -> 110 -> 80 -> 130.
    # Peak at 120 (t1), trough at 80 (t4): drawdown = 80/120 - 1 = -1/3.
    # Recovers at 130 (t5), which exceeds the 120 peak.
    prices = _series([100.0, 120.0, 90.0, 110.0, 80.0, 130.0])
    r = prices.pct_change().dropna()
    result = K.max_drawdown(r)
    assert result.max_drawdown == pytest.approx(-1 / 3)
    assert result.peak_date == pd.Timestamp("2024-01-02")
    assert result.trough_date == pd.Timestamp("2024-01-05")
    assert result.recovery_date == pd.Timestamp("2024-01-06")


def test_max_drawdown_no_recovery_within_window():
    prices = _series([100.0, 120.0, 90.0])  # never climbs back to 120
    r = prices.pct_change().dropna()
    result = K.max_drawdown(r)
    assert result.recovery_date is None


def test_sharpe_ratio_exact():
    r = _series([0.10, -0.10])
    sharpe = K.sharpe_ratio(r, risk_free_rate=0.0, periods_per_year=2)
    # annualized_return = -0.01, annualized_vol = 0.2 -> sharpe = -0.05
    assert sharpe == pytest.approx(-0.05)


def test_sharpe_ratio_rejects_zero_volatility():
    r = _series([0.01, 0.01, 0.01])  # constant returns -> zero volatility
    with pytest.raises(ValueError):
        K.sharpe_ratio(r, risk_free_rate=0.0, periods_per_year=252)


def test_covariance_and_correlation_matrix_shapes():
    panel = pd.DataFrame(
        {
            "A": [0.01, -0.02, 0.03, 0.01],
            "B": [0.02, -0.01, 0.01, 0.00],
        },
        index=pd.date_range("2024-01-01", periods=4, freq="D"),
    )
    cov = K.covariance_matrix(panel, periods_per_year=252)
    corr = K.correlation_matrix(panel)
    assert cov.shape == (2, 2)
    assert corr.shape == (2, 2)
    assert corr.loc["A", "A"] == pytest.approx(1.0)
    assert cov.loc["A", "B"] == pytest.approx(cov.loc["B", "A"])  # symmetric
