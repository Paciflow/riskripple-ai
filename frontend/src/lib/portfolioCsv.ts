/**
 * Parses a user-supplied portfolio CSV (symbol,weight rows) into a weights map.
 * Scoped to the fixed 8-asset demo universe — see pricePanel.json — because that's
 * the only data this build has real price history for. See docs/KNOWN_LIMITATIONS.md.
 */

export interface ParsedPortfolio {
  weights: Record<string, number>
  errors: string[]
  warnings: string[]
}

const WEIGHT_SUM_TOLERANCE = 0.01

export function parsePortfolioCsv(csvText: string, knownSymbols: string[]): ParsedPortfolio {
  const errors: string[] = []
  const warnings: string[] = []
  const knownSet = new Set(knownSymbols.map((s) => s.toUpperCase()))

  const lines = csvText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  if (lines.length === 0) {
    return { weights: {}, errors: ['CSV is empty.'], warnings: [] }
  }

  let dataLines = lines
  const firstCols = lines[0].split(',').map((c) => c.trim().toLowerCase())
  if (firstCols[0] === 'symbol' || firstCols[0] === 'ticker') {
    dataLines = lines.slice(1)
  }

  if (dataLines.length === 0) {
    return { weights: {}, errors: ['CSV has a header but no data rows.'], warnings: [] }
  }

  const raw: Record<string, number> = {}
  for (let i = 0; i < dataLines.length; i++) {
    const rowNum = i + 1
    const cols = dataLines[i].split(',').map((c) => c.trim())
    if (cols.length < 2) {
      errors.push(`Row ${rowNum}: expected "symbol,weight", got "${dataLines[i]}".`)
      continue
    }
    const symbol = cols[0].toUpperCase()
    const weightText = cols[1].replace('%', '')
    const parsed = Number(weightText)
    if (!symbol) {
      errors.push(`Row ${rowNum}: missing symbol.`)
      continue
    }
    if (Number.isNaN(parsed)) {
      errors.push(`Row ${rowNum}: "${cols[1]}" is not a number.`)
      continue
    }
    if (symbol in raw) {
      errors.push(`Row ${rowNum}: duplicate symbol "${symbol}" (already seen earlier in this file).`)
      continue
    }
    if (!knownSet.has(symbol)) {
      errors.push(
        `Row ${rowNum}: "${symbol}" is not in this demo's price-history universe (${knownSymbols.join(', ')}). ` +
          'Remove it or substitute a covered ticker — there is no real price data to compute metrics against.',
      )
      continue
    }
    // A value like 60 (percent) vs 0.60 (fraction) — detect by magnitude, not by the presence of "%".
    raw[symbol] = Math.abs(parsed) > 1 ? parsed / 100 : parsed
  }

  if (Object.keys(raw).length === 0) {
    return { weights: {}, errors: errors.length > 0 ? errors : ['No valid rows found.'], warnings }
  }

  if (Object.values(raw).some((w) => w < 0)) {
    errors.push('Negative weights are not supported (no short positions in this demo).')
    return { weights: {}, errors, warnings }
  }

  const total = Object.values(raw).reduce((a, b) => a + b, 0)
  if (total <= 0) {
    errors.push('Weights sum to zero or less.')
    return { weights: {}, errors, warnings }
  }

  let weights = raw
  if (Math.abs(total - 1) > WEIGHT_SUM_TOLERANCE) {
    warnings.push(`Weights summed to ${(total * 100).toFixed(1)}%, not 100% — normalized proportionally.`)
    weights = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v / total]))
  }

  return { weights, errors, warnings }
}

export function portfolioToCsv(weights: Record<string, number>): string {
  const lines = ['symbol,weight']
  for (const [symbol, w] of Object.entries(weights)) {
    lines.push(`${symbol},${(w * 100).toFixed(1)}`)
  }
  return lines.join('\n')
}
