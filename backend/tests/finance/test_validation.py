import pandas as pd
import pytest

from riskripple.finance.errors import FinanceDataError
from riskripple.finance.validation import (
    validate_price_series,
    validate_currency_consistency,
    require_valid,
)


def _series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_valid_series_passes():
    prices = _series([100.0 + i for i in range(30)])
    report = validate_price_series(prices, min_observations=20)
    assert report.is_valid
    assert report.errors == []


def test_rejects_empty_series():
    report = validate_price_series(pd.Series(dtype=float))
    assert not report.is_valid


def test_rejects_nonpositive_prices():
    prices = _series([100.0, 0.0, -5.0] + [100.0] * 20)
    report = validate_price_series(prices, min_observations=5)
    assert not report.is_valid
    assert any("nonpositive" in e for e in report.errors)


def test_rejects_duplicate_timestamps():
    idx = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"])
    prices = pd.Series([100.0, 101.0, 102.0], index=idx)
    report = validate_price_series(prices, min_observations=1)
    assert not report.is_valid
    assert any("duplicate" in e for e in report.errors)


def test_rejects_out_of_order_dates():
    idx = pd.to_datetime(["2024-01-02", "2024-01-01", "2024-01-03"])
    prices = pd.Series([100.0, 101.0, 102.0], index=idx)
    report = validate_price_series(prices, min_observations=1)
    assert not report.is_valid
    assert any("ascending" in e for e in report.errors)


def test_warns_on_missing_values_without_failing():
    prices = _series([100.0] * 25)
    prices.iloc[5] = float("nan")
    report = validate_price_series(prices, min_observations=20)
    assert report.is_valid  # missing data warns, does not reject outright
    assert any("missing" in w for w in report.warnings)


def test_insufficient_history_rejected():
    prices = _series([100.0, 101.0, 102.0])
    report = validate_price_series(prices, min_observations=20)
    assert not report.is_valid
    assert any("insufficient history" in e for e in report.errors)


def test_require_valid_raises_finance_data_error():
    prices = _series([100.0, -1.0] + [100.0] * 20)
    report = validate_price_series(prices, min_observations=5)
    with pytest.raises(FinanceDataError):
        require_valid(report)


def test_currency_consistency_warns_on_mixed_currencies():
    report = validate_currency_consistency({"SPY": "USD", "XBB.TO": "CAD"})
    assert report.is_valid  # a warning, not a hard error
    assert len(report.warnings) == 1


def test_currency_consistency_silent_when_uniform():
    report = validate_currency_consistency({"SPY": "USD", "QQQ": "USD"})
    assert report.warnings == []
