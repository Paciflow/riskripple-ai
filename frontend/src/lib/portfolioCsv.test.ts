import { describe, expect, it } from 'vitest'
import { parsePortfolioCsv, portfolioToCsv } from './portfolioCsv'

const UNIVERSE = ['SPY', 'QQQ', 'AGG', 'GLD', 'BIL', 'NVDA', 'AMD', 'INTC']

describe('parsePortfolioCsv', () => {
  it('parses a valid fraction-weighted CSV with a header', () => {
    const csv = 'symbol,weight\nSPY,0.5\nNVDA,0.5'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors).toEqual([])
    expect(result.weights.SPY).toBeCloseTo(0.5, 10)
    expect(result.weights.NVDA).toBeCloseTo(0.5, 10)
  })

  it('parses a valid CSV with no header', () => {
    const csv = 'SPY,60\nQQQ,40'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors).toEqual([])
    expect(result.weights.SPY).toBeCloseTo(0.6, 10)
    expect(result.weights.QQQ).toBeCloseTo(0.4, 10)
  })

  it('normalizes weights that do not sum to 100% and warns', () => {
    const csv = 'SPY,30\nQQQ,30'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors).toEqual([])
    expect(result.warnings.length).toBe(1)
    expect(result.weights.SPY).toBeCloseTo(0.5, 10)
  })

  it('rejects a symbol outside the known price-history universe', () => {
    const csv = 'SPY,50\nTSLA,50'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors.length).toBe(1)
    expect(result.errors[0]).toContain('TSLA')
  })

  it('rejects a duplicate symbol', () => {
    const csv = 'SPY,50\nSPY,50'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors.some((e) => e.includes('duplicate'))).toBe(true)
  })

  it('rejects negative weights', () => {
    const csv = 'SPY,-10\nQQQ,110'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors.some((e) => e.includes('Negative'))).toBe(true)
  })

  it('rejects an empty file', () => {
    const result = parsePortfolioCsv('', UNIVERSE)
    expect(result.errors).toEqual(['CSV is empty.'])
  })

  it('rejects a non-numeric weight', () => {
    const csv = 'SPY,abc'
    const result = parsePortfolioCsv(csv, UNIVERSE)
    expect(result.errors[0]).toContain('not a number')
  })
})

describe('portfolioToCsv', () => {
  it('round-trips through parsePortfolioCsv', () => {
    const original = { SPY: 0.6, QQQ: 0.4 }
    const csv = portfolioToCsv(original)
    const parsed = parsePortfolioCsv(csv, UNIVERSE)
    expect(parsed.errors).toEqual([])
    expect(parsed.weights.SPY).toBeCloseTo(0.6, 2)
    expect(parsed.weights.QQQ).toBeCloseTo(0.4, 2)
  })
})
