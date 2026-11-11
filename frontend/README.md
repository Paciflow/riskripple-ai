# RiskRipple AI — Frontend

React + Vite + TypeScript + Tailwind v4 dashboard. Ships with a frozen real-data
fixture (`src/data/demoAnalysis.json`) so it runs standalone with no backend.

## Run locally

```bash
npm install
npm run dev
```

## Regenerate the demo data fixture

The fixture is real output from the actual backend orchestrator, not hand-written.
Regenerate it after any change to the finance engine, personas, or demo scenario:

```bash
cd ../backend && source .venv/bin/activate && cd ..
python3 -c "
import sys, json; sys.path.insert(0, 'backend/src')
from riskripple.workflows.local_orchestrator import run_investigation
from riskripple.tools import finance_tools as FT

weights = {'SPY': 0.30, 'QQQ': 0.20, 'NVDA': 0.20, 'AMD': 0.10, 'INTC': 0.10, 'AGG': 0.05, 'GLD': 0.05}
analysis, report = run_investigation(
    portfolio_weights=weights, portfolio_value=100_000.0,
    event_title='Semiconductor export restrictions on advanced computing chips to China',
    event_entities=['TSMC', 'Samsung', 'SK Hynix'],
)
history = FT.load_price_history(list(weights.keys()))
returns = FT.calculate_returns(history['_panel_csv'])
held = FT.compare_allocations(returns['_returns_csv'], {'held_portfolio': weights})['held_portfolio']
corr = FT.calculate_correlation_matrix(returns['_returns_csv'])
payload = {
    'analysis': json.loads(analysis.model_dump_json()),
    'report': json.loads(report.model_dump_json()),
    'held_portfolio': held,
    'correlation_matrix': corr['correlation_matrix'],
}
json.dump(payload, open('frontend/src/data/demoAnalysis.json', 'w'), indent=2)
"
```

## Connect to a live backend

Set `VITE_API_BASE_URL` to a deployed API Gateway URL (see
`docs/AWS_DEPLOYMENT.md`) in a `.env.local` or `.env.production` file. Without it,
the app always reads `demoAnalysis.json` — this path has not been tested against a
live API yet (no backend has been deployed from the development AWS account; see
`docs/KNOWN_LIMITATIONS.md`).

## Pages

Dashboard, Event Intelligence, Portfolio Analyzer, Ripple Graph, Scenario
Simulator, Persona Comparison, Investigation Report — one route each, see
`src/App.tsx`.

## Verification

`npm run build` (TypeScript + Vite production build, `tsc -b` then `vite build`)
passes clean, and the dev server was confirmed to serve the app and respond on all
routes. A headless-browser visual check (Playwright) was attempted but the
Chromium download never completed in this sandboxed environment (network access
to its CDN redirected but stalled indefinitely); it was removed rather than left
in a non-working state. **No one has visually confirmed the rendered pages** —
before the demo, run `npm run dev` and click through all 7 routes yourself at
least once.
