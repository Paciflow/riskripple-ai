import { useMemo, useRef, useState } from 'react'
import pricePanel from '../data/pricePanel.json'
import {
  annualizedReturn,
  annualizedVolatility,
  correlationMatrix,
  dailyReturns,
  herfindahlIndex,
  maxDrawdown,
  maxSingleAssetWeight,
  normalizeWeights,
  portfolioReturns,
  sharpeRatio,
} from '../lib/finance'
import { parsePortfolioCsv, portfolioToCsv } from '../lib/portfolioCsv'
import { Card, Pill, StatCard } from './ui'
import { DEMO_PORTFOLIO_WEIGHTS } from '../types'

const UNIVERSE: string[] = pricePanel.symbols

function correlationColor(v: number): string {
  if (v >= 0) return `rgba(79,156,249,${v * 0.8})`
  return `rgba(248,113,113,${-v * 0.8})`
}

function equalWeights(symbols: string[]): Record<string, number> {
  const w = 1 / symbols.length
  return Object.fromEntries(symbols.map((s) => [s, w]))
}

export default function PortfolioBuilder() {
  const [weights, setWeights] = useState<Record<string, number>>(DEMO_PORTFOLIO_WEIGHTS)
  const [showPaste, setShowPaste] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const returnsBySymbol = useMemo(() => {
    const out: Record<string, number[]> = {}
    for (const s of UNIVERSE) out[s] = dailyReturns(pricePanel.adj_close[s as keyof typeof pricePanel.adj_close])
    return out
  }, [])

  const activeWeights = useMemo(() => {
    const nonZero = Object.fromEntries(Object.entries(weights).filter(([, w]) => w > 0))
    if (Object.keys(nonZero).length === 0) return null
    try {
      return normalizeWeights(nonZero)
    } catch {
      return null
    }
  }, [weights])

  const metrics = useMemo(() => {
    if (!activeWeights) return null
    try {
      const relevantReturns = Object.fromEntries(Object.keys(activeWeights).map((s) => [s, returnsBySymbol[s]]))
      const pr = portfolioReturns(relevantReturns, activeWeights)
      const [topAsset, topWeight] = maxSingleAssetWeight(activeWeights)
      return {
        annualizedReturn: annualizedReturn(pr),
        annualizedVolatility: annualizedVolatility(pr),
        sharpeRatio: sharpeRatio(pr, 0),
        maxDrawdown: maxDrawdown(pr).maxDrawdown,
        herfindahl: herfindahlIndex(activeWeights),
        topAsset,
        topWeight,
        correlation: correlationMatrix(relevantReturns),
        symbols: Object.keys(activeWeights),
      }
    } catch {
      return null
    }
  }, [activeWeights, returnsBySymbol])

  function applyParsed(csv: string) {
    const result = parsePortfolioCsv(csv, UNIVERSE)
    setErrors(result.errors)
    setWarnings(result.warnings)
    if (result.errors.length === 0 && Object.keys(result.weights).length > 0) {
      setWeights(Object.fromEntries(UNIVERSE.map((s) => [s, result.weights[s] ?? 0])))
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => applyParsed(String(reader.result ?? ''))
    reader.readAsText(file)
    e.target.value = ''
  }

  function handleWeightInput(symbol: string, pctText: string) {
    const pct = Number(pctText)
    setErrors([])
    setWarnings([])
    setWeights((prev) => ({ ...prev, [symbol]: Number.isNaN(pct) ? 0 : pct / 100 }))
  }

  const templateHref =
    'data:text/csv;charset=utf-8,' + encodeURIComponent(portfolioToCsv(DEMO_PORTFOLIO_WEIGHTS))

  const rawTotal = Object.values(weights).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-dim)' }}>
            Live Portfolio Calculator
          </h3>
          <Pill tone="neutral">Computed in your browser — no backend required</Pill>
        </div>
        <p className="text-xs mb-4" style={{ color: 'var(--color-text-dim)' }}>
          Edit weights below, or upload/paste a CSV ("symbol,weight" rows). Limited to this
          demo's price-history universe ({UNIVERSE.join(', ')}), real adjusted-close data,
          {' '}{pricePanel.dates[0]} to {pricePanel.dates[pricePanel.dates.length - 1]}.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {UNIVERSE.map((s) => (
            <label key={s} className="flex flex-col gap-1">
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-dim)' }}>
                {s}
              </span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={+((weights[s] ?? 0) * 100).toFixed(2)}
                  onChange={(e) => handleWeightInput(s, e.target.value)}
                  className="w-full rounded px-2 py-1 text-sm"
                  style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                />
                <span className="text-xs" style={{ color: 'var(--color-text-dim)' }}>%</span>
              </div>
            </label>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-wrap mb-4">
          <button
            type="button"
            onClick={() => {
              setErrors([])
              setWarnings([])
              setWeights(equalWeights(UNIVERSE))
            }}
            className="rounded px-3 py-1.5 text-xs font-medium"
            style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}
          >
            Equal-weight
          </button>
          <button
            type="button"
            onClick={() => {
              setErrors([])
              setWarnings([])
              setWeights(DEMO_PORTFOLIO_WEIGHTS)
            }}
            className="rounded px-3 py-1.5 text-xs font-medium"
            style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}
          >
            Reset to demo portfolio
          </button>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded px-3 py-1.5 text-xs font-medium"
            style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}
          >
            Upload CSV
          </button>
          <input ref={fileInputRef} type="file" accept=".csv,text/csv" onChange={handleFileUpload} className="hidden" />
          <button
            type="button"
            onClick={() => setShowPaste((v) => !v)}
            className="rounded px-3 py-1.5 text-xs font-medium"
            style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}
          >
            {showPaste ? 'Hide paste box' : 'Paste CSV'}
          </button>
          <a
            href={templateHref}
            download="portfolio_template.csv"
            className="rounded px-3 py-1.5 text-xs font-medium hover:underline"
            style={{ color: 'var(--color-accent)' }}
          >
            Download CSV template
          </a>
          <span className="text-xs ml-auto" style={{ color: Math.abs(rawTotal - 1) > 0.01 ? 'var(--color-warn)' : 'var(--color-text-dim)' }}>
            Sum: {(rawTotal * 100).toFixed(1)}%
          </span>
        </div>

        {showPaste && (
          <div className="mb-4">
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="symbol,weight&#10;SPY,60&#10;NVDA,40"
              rows={4}
              className="w-full rounded px-3 py-2 text-xs font-mono"
              style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
            />
            <button
              type="button"
              onClick={() => applyParsed(pasteText)}
              className="mt-2 rounded px-3 py-1.5 text-xs font-medium"
              style={{ background: 'var(--color-accent)', color: 'var(--color-bg)' }}
            >
              Parse
            </button>
          </div>
        )}

        {errors.length > 0 && (
          <ul className="mb-4 text-xs space-y-1" style={{ color: 'var(--color-bad)' }}>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
        {warnings.length > 0 && (
          <ul className="mb-4 text-xs space-y-1" style={{ color: 'var(--color-warn)' }}>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}

        {!metrics && (
          <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
            Enter at least one positive weight to compute metrics.
          </p>
        )}
      </Card>

      {metrics && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Annualized Return" value={`${(metrics.annualizedReturn * 100).toFixed(1)}%`} tone="good" />
            <StatCard label="Annualized Volatility" value={`${(metrics.annualizedVolatility * 100).toFixed(1)}%`} tone="warn" />
            <StatCard label="Sharpe Ratio (rf=0)" value={metrics.sharpeRatio.toFixed(2)} />
            <StatCard label="Max Drawdown" value={`${(metrics.maxDrawdown * 100).toFixed(1)}%`} tone="bad" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <StatCard
              label="Concentration (HHI)"
              value={metrics.herfindahl.toFixed(3)}
              hint={`1/n for equal-weight across n assets; 1.0 = single asset`}
            />
            <StatCard label="Largest Single Position" value={`${metrics.topAsset} (${(metrics.topWeight * 100).toFixed(1)}%)`} />
          </div>

          <Card>
            <h3 className="text-sm font-medium mb-4" style={{ color: 'var(--color-text-dim)' }}>
              Correlation Matrix (held weights only)
            </h3>
            <div className="overflow-x-auto">
              <table className="text-xs border-collapse">
                <thead>
                  <tr>
                    <th className="p-2" />
                    {metrics.symbols.map((s) => (
                      <th key={s} className="p-2 font-medium" style={{ color: 'var(--color-text-dim)' }}>
                        {s}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.symbols.map((row) => (
                    <tr key={row}>
                      <td className="p-2 font-medium" style={{ color: 'var(--color-text-dim)' }}>
                        {row}
                      </td>
                      {metrics.symbols.map((col) => (
                        <td
                          key={col}
                          className="p-2 text-center rounded"
                          style={{ background: correlationColor(metrics.correlation[row][col]) }}
                        >
                          {metrics.correlation[row][col].toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
