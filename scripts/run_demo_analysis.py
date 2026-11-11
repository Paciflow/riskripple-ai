#!/usr/bin/env python3
"""End-to-end smoke test / CLI demo: real frozen market data -> finance engine ->
persona comparison -> stress scenarios. No AWS required.

Usage: python scripts/run_demo_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from riskripple.finance import returns as R
from riskripple.finance.stress import DEMO_SCENARIOS
from riskripple.ingestion.market_data import SnapshotMarketDataProvider
from riskripple.personas import policies as P
from riskripple.schemas.models import PersonaName

SNAPSHOT_DIR = REPO_ROOT / "data" / "fixtures" / "market"
UNIVERSE = ["SPY", "QQQ", "AGG", "GLD", "BIL", "NVDA", "AMD", "INTC"]


def main() -> None:
    provider = SnapshotMarketDataProvider(SNAPSHOT_DIR)

    price_series = {}
    for symbol in UNIVERSE:
        result = provider.load(symbol)
        price_series[symbol] = result.prices["adj_close"]
        print(
            f"{symbol}: {len(result.prices)} obs, source={result.metadata.source_name}, "
            f"as of {result.metadata.observation_date}"
        )

    panel = R.align_price_panel(price_series)
    returns_panel = R.returns_panel(panel)
    print(f"\nAligned trading calendar: {len(returns_panel)} common sessions "
          f"({returns_panel.index.min().date()} to {returns_panel.index.max().date()})")

    scenarios = {name: s for name, s in DEMO_SCENARIOS.items()}
    results = P.compare_personas(list(PersonaName), returns_panel, scenarios=scenarios)

    print("\n--- Persona comparison (real historical data, hypothetical stress scenarios) ---")
    for ev in results:
        print(f"\n{ev.persona.value.upper()}")
        print(f"  allocation: {{ {', '.join(f'{k}: {v:.1%}' for k, v in sorted(ev.proposed_weights.items(), key=lambda kv: -kv[1]))} }}")
        print(f"  historical annualized return: {ev.annualized_return:.2%}")
        print(f"  historical annualized volatility: {ev.annualized_volatility:.2%}")
        print(f"  Sharpe (rf=0): {ev.sharpe_ratio:.2f}")
        print(f"  historical max drawdown: {ev.max_drawdown:.2%}")
        print(f"  concentration (HHI): {ev.herfindahl_index:.3f}")
        print(f"  constraint violations: {ev.constraint_violations or 'none'}")
        print("  hypothetical scenario P&L on $100,000:")
        for name, pnl in ev.scenario_pnl.items():
            print(f"    {name}: ${pnl:,.0f}")


if __name__ == "__main__":
    main()
