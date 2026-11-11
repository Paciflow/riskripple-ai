import pandas as pd
import pytest

from riskripple.finance import returns as R


def _series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_daily_returns_exact():
    prices = _series([100.0, 110.0, 99.0])
    r = R.daily_returns(prices)
    assert r.iloc[0] == pytest.approx(0.10)
    assert r.iloc[1] == pytest.approx(-0.10)
    assert len(r) == 2  # first observation has no prior price


def test_annualized_return_is_geometric_not_arithmetic():
    # +10% then -10%: arithmetic mean is 0%, but compounding destroys value (-1%).
    r = _series([0.10, -0.10])
    geometric = R.annualized_return(r, periods_per_year=2)
    arithmetic = R.arithmetic_mean_return(r, periods_per_year=2)
    assert geometric == pytest.approx(-0.01)
    assert arithmetic == pytest.approx(0.0)
    assert geometric != arithmetic


def test_annualized_return_rejects_empty_series():
    with pytest.raises(ValueError):
        R.annualized_return(pd.Series(dtype=float))


def test_annualized_return_rejects_total_wipeout():
    r = _series([-1.0])  # -100% return: cumulative growth is zero
    with pytest.raises(ValueError):
        R.annualized_return(r, periods_per_year=1)


def test_cumulative_wealth_matches_price_ratios():
    prices = _series([100.0, 120.0, 90.0])
    r = R.daily_returns(prices)
    wealth = R.cumulative_wealth(r)
    assert wealth.iloc[0] == pytest.approx(1.2)
    assert wealth.iloc[1] == pytest.approx(0.9)


def test_align_price_panel_inner_joins_on_common_dates():
    a = _series([10.0, 11.0, 12.0], start="2024-01-01")
    b = _series([20.0, 21.0], start="2024-01-02")  # starts one day later, shorter
    panel = R.align_price_panel({"A": a, "B": b})
    assert list(panel.index) == list(pd.date_range("2024-01-02", periods=2, freq="D"))
    assert panel.shape == (2, 2)


def test_align_price_panel_rejects_no_overlap():
    a = _series([10.0, 11.0], start="2024-01-01")
    b = _series([20.0, 21.0], start="2024-06-01")
    with pytest.raises(ValueError):
        R.align_price_panel({"A": a, "B": b})
