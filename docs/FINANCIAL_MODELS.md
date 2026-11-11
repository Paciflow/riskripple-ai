# Financial Models

All formulas below are implemented in `backend/src/riskripple/finance/` and unit
tested against hand-verified synthetic values in `backend/tests/finance/`.

## Returns

**Daily simple return:** `r_t = P_t / P_(t-1) - 1`, computed on the
adjusted-close series (`finance/returns.py:daily_returns`). Adjusted close is used
throughout — the code explicitly refuses to silently fall back to unadjusted close
if a data source doesn't provide one (`ingestion/market_data.py`).

**Annualized return — geometric, not arithmetic:**

```
annualized = (prod(1 + r_i)) ** (periods_per_year / n) - 1
```

This is deliberate: the arithmetic mean annualized return systematically overstates
performance for volatile series (volatility drag is real money, not a rounding
error). `finance/returns.py` provides both `annualized_return` (geometric, the one
used for reporting) and `arithmetic_mean_return` (diagnostic only) so the gap
between them is visible, not hidden.

## Volatility

```
sigma_annual = std(daily_returns, ddof=1) * sqrt(periods_per_year)
```

Sample standard deviation (`ddof=1`) is used, consistent with estimating volatility
from a finite historical sample rather than treating it as a known population
parameter.

## Portfolio aggregation

```
R_p = sum(w_i * R_i)
sigma_p = sqrt(w^T * Covariance * w)
```

`Covariance` is the annualized sample covariance matrix
(`finance/risk.py:covariance_matrix`).

## Max drawdown

Cumulative wealth `W_t = prod(1 + r_i)` for `i <= t`; running peak
`peak_t = max(W_0..W_t)`; drawdown `d_t = W_t / peak_t - 1`; max drawdown is
`min(d_t)`. The implementation also reports the peak date, trough date, and
recovery date (or `None` if the series never recovers within the window) —
not just the single number.

## Sharpe ratio

```
Sharpe = (annualized_return - risk_free_rate) / annualized_volatility
```

`risk_free_rate` must be supplied as an already-annualized rate in the same
currency as the return series; the caller is responsible for currency consistency
(checked by `finance/validation.validate_currency_consistency`).

## Concentration

Herfindahl-Hirschman Index: `HHI = sum(w_i^2)` (1.0 for a single-asset portfolio,
`1/n` for an equal-weight n-asset portfolio). Also reports the single largest
position and sector-level concentration.

## Stress testing

```
Delta_V = sum(position_value_i * assumed_shock_i)
```

Every `StressTestResult` carries an explicit `assumptions_label` stating the shock
values are hypothetical assumptions, not a forecast, and separately lists which
held assets had **no** shock assumption supplied (treated as 0%, but disclosed,
never silently assumed).

## Persona policy engine

Each persona (Prudent / Équilibré / Audacieux) is a set of constraints (max equity
allocation, max single-asset weight, max equity-sector concentration, drawdown
tolerance, minimum defensive allocation) — never a hardcoded "optimal" portfolio.
`personas/policies.generate_candidate_allocation` builds a candidate deterministically
from those constraints, and `check_constraint_violations` reports — rather than
silently hides — cases where the demo's limited asset universe can't fully satisfy a
persona's own policy (e.g., a single bond ETF can't satisfy a 15% max-single-asset
cap when it needs to hold 40%+ of the defensive sleeve). This is treated as an honest
finding to surface in the report, not a bug to paper over.

**Important scoping fix found via testing:** the equity-sector concentration check
only applies to equity-classified holdings. An earlier version also summed
bond/cash weights into the same "sector" concentration check, which fired
nonsensical violations (e.g., "35% in fixed_income exceeds the sector cap") that
were really just restating the persona's own minimum-defensive-allocation
requirement. Fixed by scoping the sector check to equities only.

## Data integrity checks

`finance/validation.py` rejects or explicitly qualifies (never silently proceeds
past): empty series, non-`DatetimeIndex` series, duplicate timestamps, out-of-order
dates, nonpositive prices, and insufficient history (configurable minimum
observation count). Missing values warn rather than reject, since a few scattered
NaNs are common and recoverable via `dropna`, but silent full failures are not.
