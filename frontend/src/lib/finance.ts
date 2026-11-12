/**
 * Client-side port of backend/src/riskripple/finance/{returns,risk,portfolio}.py.
 * Formulas must stay numerically identical to the Python versions — see
 * docs/FINANCIAL_MODELS.md. Ported so the Portfolio Analyzer page can compute
 * real metrics for a user-edited/uploaded weighting without a deployed backend.
 */

export const TRADING_DAYS_PER_YEAR = 252

export class FinanceDataError extends Error {}

/** Simple daily returns: r_t = P_t / P_(t-1) - 1. */
export function dailyReturns(prices: number[]): number[] {
  const out: number[] = []
  for (let i = 1; i < prices.length; i++) {
    out.push(prices[i] / prices[i - 1] - 1)
  }
  return out
}

/** Geometric (compound) annualized return — not the arithmetic mean. */
export function annualizedReturn(returns: number[], periodsPerYear = TRADING_DAYS_PER_YEAR): number {
  const n = returns.length
  if (n === 0) throw new FinanceDataError('cannot annualize an empty return series')
  const totalGrowth = returns.reduce((acc, r) => acc * (1 + r), 1)
  if (totalGrowth <= 0) {
    throw new FinanceDataError('cumulative growth is nonpositive; check for a -100% or worse return')
  }
  return Math.pow(totalGrowth, periodsPerYear / n) - 1
}

/** Sample standard deviation (ddof=1), annualized by sqrt(periodsPerYear). */
export function annualizedVolatility(returns: number[], periodsPerYear = TRADING_DAYS_PER_YEAR): number {
  if (returns.length < 2) {
    throw new FinanceDataError('need at least 2 return observations to estimate volatility')
  }
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length
  const sumSq = returns.reduce((acc, r) => acc + (r - mean) ** 2, 0)
  const sampleVariance = sumSq / (returns.length - 1)
  return Math.sqrt(sampleVariance) * Math.sqrt(periodsPerYear)
}

export function sharpeRatio(returns: number[], riskFreeRate: number, periodsPerYear = TRADING_DAYS_PER_YEAR): number {
  const annReturn = annualizedReturn(returns, periodsPerYear)
  const annVol = annualizedVolatility(returns, periodsPerYear)
  if (annVol === 0) throw new FinanceDataError('annualized volatility is zero; Sharpe ratio is undefined')
  return (annReturn - riskFreeRate) / annVol
}

export interface DrawdownResult {
  maxDrawdown: number
  peakIndex: number
  troughIndex: number
  recoveryIndex: number | null
}

/** Largest peak-to-trough decline in cumulative wealth, over a return series. */
export function maxDrawdown(returns: number[]): DrawdownResult {
  const wealth: number[] = []
  let w = 1
  for (const r of returns) {
    w *= 1 + r
    wealth.push(w)
  }
  const runningPeak: number[] = []
  let peak = -Infinity
  for (const v of wealth) {
    peak = Math.max(peak, v)
    runningPeak.push(peak)
  }
  const drawdown = wealth.map((v, i) => v / runningPeak[i] - 1)

  let troughIndex = 0
  for (let i = 1; i < drawdown.length; i++) {
    if (drawdown[i] < drawdown[troughIndex]) troughIndex = i
  }
  const mdd = drawdown[troughIndex]

  let peakIndex = 0
  for (let i = 1; i <= troughIndex; i++) {
    if (wealth[i] > wealth[peakIndex]) peakIndex = i
  }
  const peakValue = wealth[peakIndex]

  let recoveryIndex: number | null = null
  for (let i = troughIndex; i < wealth.length; i++) {
    if (wealth[i] >= peakValue) {
      recoveryIndex = i
      break
    }
  }

  return { maxDrawdown: mdd, peakIndex, troughIndex, recoveryIndex }
}

/** Pairwise Pearson correlation of asset return series (not annualized — scale-free). */
export function correlationMatrix(returnsBySymbol: Record<string, number[]>): Record<string, Record<string, number>> {
  const symbols = Object.keys(returnsBySymbol)
  const means: Record<string, number> = {}
  const stds: Record<string, number> = {}
  for (const s of symbols) {
    const r = returnsBySymbol[s]
    const mean = r.reduce((a, b) => a + b, 0) / r.length
    means[s] = mean
    stds[s] = Math.sqrt(r.reduce((acc, v) => acc + (v - mean) ** 2, 0) / (r.length - 1))
  }
  const matrix: Record<string, Record<string, number>> = {}
  for (const a of symbols) {
    matrix[a] = {}
    for (const b of symbols) {
      const ra = returnsBySymbol[a]
      const rb = returnsBySymbol[b]
      const n = ra.length
      let cov = 0
      for (let i = 0; i < n; i++) cov += (ra[i] - means[a]) * (rb[i] - means[b])
      cov /= n - 1
      matrix[a][b] = stds[a] === 0 || stds[b] === 0 ? 0 : cov / (stds[a] * stds[b])
    }
  }
  return matrix
}

/** R_p,t = sum_i(w_i * R_i,t). */
export function portfolioReturns(returnsBySymbol: Record<string, number[]>, weights: Record<string, number>): number[] {
  const symbols = Object.keys(weights)
  const n = returnsBySymbol[symbols[0]].length
  const out: number[] = new Array(n).fill(0)
  for (const s of symbols) {
    const w = weights[s]
    const r = returnsBySymbol[s]
    for (let i = 0; i < n; i++) out[i] += w * r[i]
  }
  return out
}

export function herfindahlIndex(weights: Record<string, number>): number {
  return Object.values(weights).reduce((acc, w) => acc + w ** 2, 0)
}

export function maxSingleAssetWeight(weights: Record<string, number>): [string, number] {
  let best: [string, number] = ['', -Infinity]
  for (const [asset, w] of Object.entries(weights)) {
    if (w > best[1]) best = [asset, w]
  }
  return best
}

export function normalizeWeights(weights: Record<string, number>): Record<string, number> {
  const total = Object.values(weights).reduce((a, b) => a + b, 0)
  if (total <= 0) throw new FinanceDataError('portfolio weights must sum to a positive number')
  const out: Record<string, number> = {}
  for (const [k, v] of Object.entries(weights)) out[k] = v / total
  return out
}
