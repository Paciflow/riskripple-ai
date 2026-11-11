"""Agent 4 (Quantitative Risk Analyst) tool surface.

Every tool here calls a deterministic Python function in riskripple.finance; the LLM
driving the agent never performs arithmetic itself, only orchestrates which tool to
call and interprets the structured numeric result (master spec section 9, Agent 4).
"""
from __future__ import annotations

import pandas as pd
from strands import tool

from riskripple.config import FIXTURES_DIR
from riskripple.finance import portfolio as P, returns as R, risk as K
from riskripple.finance.stress import DEMO_SCENARIOS, run_stress_test
from riskripple.ingestion.market_data import SnapshotMarketDataProvider

_DEFAULT_SNAPSHOT_DIR = FIXTURES_DIR / "market"


@tool
def load_price_history(symbols: list[str], snapshot_dir: str | None = None) -> dict:
    """Load adjusted-close price history for a list of symbols from the frozen demo
    snapshot, aligned onto a shared trading calendar. Returns per-symbol source
    provenance so results can be cited by date and source.
    """
    provider = SnapshotMarketDataProvider(snapshot_dir or _DEFAULT_SNAPSHOT_DIR)
    price_series, provenance = {}, {}
    for symbol in symbols:
        result = provider.load(symbol)
        price_series[symbol] = result.prices["adj_close"]
        provenance[symbol] = {
            "source_name": result.metadata.source_name,
            "source_url": result.metadata.source_url,
            "observation_date": str(result.metadata.observation_date),
            "currency": result.metadata.currency,
        }
    panel = R.align_price_panel(price_series)
    return {
        "symbols": symbols,
        "start_date": str(panel.index.min().date()),
        "end_date": str(panel.index.max().date()),
        "n_observations": len(panel),
        "provenance": provenance,
        "_panel_csv": panel.to_csv(),  # machine-readable payload for chained tool calls
    }


def _panel_from_csv(csv_text: str) -> pd.DataFrame:
    import io
    return pd.read_csv(io.StringIO(csv_text), index_col=0, parse_dates=True)


@tool
def calculate_returns(price_panel_csv: str) -> dict:
    """Daily simple returns for each asset in a price panel (as returned by
    load_price_history's `_panel_csv` field)."""
    panel = _panel_from_csv(price_panel_csv)
    returns_panel = R.returns_panel(panel)
    return {"_returns_csv": returns_panel.to_csv(), "n_observations": len(returns_panel)}


@tool
def calculate_volatility(returns_panel_csv: str, symbol: str) -> dict:
    """Annualized sample volatility for one asset's return series."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    vol = K.annualized_volatility(returns_panel[symbol])
    return {"symbol": symbol, "annualized_volatility": vol}


@tool
def calculate_correlation_matrix(returns_panel_csv: str) -> dict:
    """Pairwise correlation matrix across all assets in a returns panel."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    corr = K.correlation_matrix(returns_panel)
    return {"correlation_matrix": corr.round(4).to_dict()}


@tool
def calculate_max_drawdown(returns_panel_csv: str, symbol: str) -> dict:
    """Historical maximum drawdown for one asset, with peak/trough/recovery dates."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    result = K.max_drawdown(returns_panel[symbol])
    return {
        "symbol": symbol,
        "max_drawdown": result.max_drawdown,
        "peak_date": str(result.peak_date.date()),
        "trough_date": str(result.trough_date.date()),
        "recovery_date": str(result.recovery_date.date()) if result.recovery_date is not None else None,
    }


@tool
def calculate_sharpe_ratio(returns_panel_csv: str, symbol: str, risk_free_rate: float = 0.0) -> dict:
    """Sharpe ratio for one asset given an annualized risk-free rate."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    sharpe = K.sharpe_ratio(returns_panel[symbol], risk_free_rate=risk_free_rate)
    return {"symbol": symbol, "sharpe_ratio": sharpe, "risk_free_rate_assumed": risk_free_rate}


@tool
def calculate_portfolio_exposure(weights: dict[str, float]) -> dict:
    """Concentration metrics for a given weight allocation: HHI and largest single
    position."""
    normalized = P.normalize_weights(weights)
    asset, max_w = P.max_single_asset_weight(normalized)
    return {
        "weights": normalized,
        "herfindahl_index": P.herfindahl_index(normalized),
        "largest_position": {"symbol": asset, "weight": max_w},
    }


@tool
def run_stress_test_tool(portfolio_value: float, weights: dict[str, float], scenario_name: str) -> dict:
    """Run one of the pre-defined hypothetical stress scenarios ('mild', 'moderate',
    'severe') against a weighted portfolio. Always returns results labeled as
    hypothetical, never as a prediction."""
    if scenario_name not in DEMO_SCENARIOS:
        raise ValueError(f"unknown scenario '{scenario_name}'; choose from {list(DEMO_SCENARIOS)}")
    result = run_stress_test(portfolio_value, P.normalize_weights(weights), DEMO_SCENARIOS[scenario_name])
    return {
        "scenario_name": result.scenario_name,
        "portfolio_value_before": result.portfolio_value_before,
        "portfolio_pnl": result.portfolio_pnl,
        "portfolio_value_after": result.portfolio_value_after,
        "position_pnl": result.position_pnl,
        "unshocked_assets": result.unshocked_assets,
        "assumptions_label": result.assumptions_label,
    }


@tool
def compare_allocations(returns_panel_csv: str, allocations: dict[str, dict[str, float]]) -> dict:
    """Compare historical annualized return/volatility/Sharpe/drawdown across several
    named candidate allocations (e.g. {"prudent": {...weights...}, "audacieux": {...}})
    computed from the same historical return data."""
    returns_panel = _panel_from_csv(returns_panel_csv)
    comparison = {}
    for name, weights in allocations.items():
        normalized = P.normalize_weights(weights)
        port_returns = P.portfolio_returns(returns_panel, normalized)
        comparison[name] = {
            "weights": normalized,
            "annualized_return": R.annualized_return(port_returns),
            "annualized_volatility": K.annualized_volatility(port_returns),
            "sharpe_ratio": K.sharpe_ratio(port_returns, risk_free_rate=0.0),
            "max_drawdown": K.max_drawdown(port_returns).max_drawdown,
        }
    return comparison


ALL_FINANCE_TOOLS = [
    load_price_history,
    calculate_returns,
    calculate_volatility,
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_portfolio_exposure,
    run_stress_test_tool,
    compare_allocations,
]
