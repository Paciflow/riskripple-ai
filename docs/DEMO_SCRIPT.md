# 5-Minute Demo Script

**Scenario:** a fictional $100,000 portfolio (SPY, QQQ, NVDA, AMD, INTC, AGG, GLD)
facing a simulated U.S. semiconductor export-restriction event affecting advanced
computing chips to China.

## 1. Dashboard (30s)

Open the Dashboard. Point out: real historical annualized return/volatility/max
drawdown for the actual held portfolio (not a persona alternative — this is the
literal demo allocation), computed from real Yahoo Finance adjusted-close data.

## 2. Event Intelligence (45s)

Navigate to Event Intelligence. Show the event summary and the facts list. Click
through to a citation — it's a real SEC 10-K accession number, not a placeholder.

## 3. Ripple Graph (60s)

Navigate to the Ripple Graph. Click an edge, e.g. NVDA → TSMC. Read the evidence
panel: it's the literal sentence from NVIDIA's actual FY2026 10-K ("We utilize
foundries, such as Taiwan Semiconductor Manufacturing Company Limited, or TSMC...").
Emphasize: **every edge here came from a literal keyword match in real filing text,
not an LLM guess.**

## 4. Portfolio Analyzer (45s)

Upload a CSV (or just edit the weight boxes) in the "Live Portfolio Calculator" —
real metrics recompute in the browser instantly, no backend call. Then scroll to
the frozen scenario section below it and show the correlation matrix — real
Pearson correlations from the aligned trading calendar.

## 5. Scenario Simulator (45s)

Show the mild/moderate/severe P&L bars by persona. Say explicitly: these are
hypothetical assumption-based shocks, not a forecast — and the UI says so too.

## 6. Persona Comparison (60s)

Select Prudent vs. Audacieux. Walk through: different candidate allocations, very
different volatility/drawdown, and — important honesty point — show a constraint
violation (e.g., "equity sector concentration in technology exceeds persona max").
This demonstrates the system catches and reports when its own generated allocation
doesn't fully satisfy the persona it was built for, rather than hiding it.

## 7. Investigation Report (30s)

Show the full report: facts vs. assumptions vs. AI interpretation vs. limitations,
all visually separated. Click Export JSON.

## Closing line

"Every number on every page traces back to either a deterministic calculation in our
finance engine, or a real public data source we can cite by name, date, and URL. The
AI's job here was never to produce numbers — only to interpret and explain the ones
the code already computed."
