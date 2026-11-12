import { describe, expect, it } from 'vitest'
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
} from './finance'

// Same synthetic cases as backend/tests/finance/* — these must match exactly,
// since this module is a parallel implementation, not a generated one.

describe('dailyReturns', () => {
  it('matches pandas pct_change semantics', () => {
    const r = dailyReturns([100, 110, 99])
    expect(r[0]).toBeCloseTo(0.1, 10)
    expect(r[1]).toBeCloseTo(-0.1, 10)
    expect(r.length).toBe(2)
  })
})

describe('annualizedReturn', () => {
  it('is geometric, not arithmetic: +10% then -10% annualizes to -1%', () => {
    const geometric = annualizedReturn([0.1, -0.1], 2)
    expect(geometric).toBeCloseTo(-0.01, 10)
  })

  it('rejects an empty series', () => {
    expect(() => annualizedReturn([])).toThrow()
  })

  it('rejects a -100% wipeout', () => {
    expect(() => annualizedReturn([-1.0], 1)).toThrow()
  })
})

describe('annualizedVolatility', () => {
  it('matches sample std (ddof=1) annualized: sqrt(0.02)*sqrt(2) = 0.2', () => {
    const vol = annualizedVolatility([0.1, -0.1], 2)
    expect(vol).toBeCloseTo(0.2, 10)
  })

  it('requires at least 2 observations', () => {
    expect(() => annualizedVolatility([0.05])).toThrow()
  })
})

describe('sharpeRatio', () => {
  it('matches annualized_return / annualized_volatility = -0.05', () => {
    const sharpe = sharpeRatio([0.1, -0.1], 0.0, 2)
    expect(sharpe).toBeCloseTo(-0.05, 10)
  })

  it('rejects zero volatility', () => {
    expect(() => sharpeRatio([0.01, 0.01, 0.01], 0.0, 252)).toThrow()
  })
})

describe('maxDrawdown', () => {
  it('matches the known path 100 -> 120 -> 90 -> 110 -> 80 -> 130', () => {
    const prices = [100, 120, 90, 110, 80, 130]
    const returns = dailyReturns(prices)
    const result = maxDrawdown(returns)
    // Prices index: 0=100,1=120,2=90,3=110,4=80,5=130 -> returns index i corresponds to price index i+1.
    expect(result.maxDrawdown).toBeCloseTo(-1 / 3, 10)
    expect(result.peakIndex).toBe(0) // returns[0] -> price 120 (peak)
    expect(result.troughIndex).toBe(3) // returns[3] -> price 80 (trough)
    expect(result.recoveryIndex).toBe(4) // returns[4] -> price 130 (recovers)
  })

  it('reports no recovery when the series never climbs back to the peak', () => {
    const prices = [100, 120, 90]
    const returns = dailyReturns(prices)
    const result = maxDrawdown(returns)
    expect(result.recoveryIndex).toBeNull()
  })
})

describe('correlationMatrix', () => {
  it('has 1.0 on the diagonal and is symmetric', () => {
    const data = {
      A: [0.01, -0.02, 0.03, 0.01],
      B: [0.02, -0.01, 0.01, 0.0],
    }
    const corr = correlationMatrix(data)
    expect(corr.A.A).toBeCloseTo(1.0, 10)
    expect(corr.A.B).toBeCloseTo(corr.B.A, 10)
  })
})

describe('portfolioReturns', () => {
  it('computes the weighted sum per period', () => {
    const data = { A: [0.1, 0.2], B: [-0.1, 0.0] }
    const pr = portfolioReturns(data, { A: 0.5, B: 0.5 })
    expect(pr[0]).toBeCloseTo(0.0, 10)
    expect(pr[1]).toBeCloseTo(0.1, 10)
  })
})

describe('herfindahlIndex / maxSingleAssetWeight / normalizeWeights', () => {
  it('computes HHI as sum of squared weights', () => {
    expect(herfindahlIndex({ A: 0.5, B: 0.5 })).toBeCloseTo(0.5, 10)
  })

  it('finds the max-weight asset', () => {
    const [asset, w] = maxSingleAssetWeight({ A: 0.3, B: 0.7 })
    expect(asset).toBe('B')
    expect(w).toBeCloseTo(0.7, 10)
  })

  it('normalizes weights to sum to 1', () => {
    const normalized = normalizeWeights({ A: 2, B: 2 })
    expect(normalized.A).toBeCloseTo(0.5, 10)
    expect(normalized.B).toBeCloseTo(0.5, 10)
  })

  it('rejects a nonpositive total', () => {
    expect(() => normalizeWeights({ A: -1, B: 0 })).toThrow()
  })
})
