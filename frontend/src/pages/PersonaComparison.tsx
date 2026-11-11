import { useState } from 'react'
import { DEMO_ANALYSIS } from '../lib/api'
import { PERSONA_LABELS, type PersonaName } from '../types'
import { Card, PageHeader, Pill, SimulationBanner } from '../components/ui'

export default function PersonaComparison() {
  const { persona_evaluations } = DEMO_ANALYSIS.analysis
  const allPersonas = persona_evaluations.map((e) => e.persona)
  const [selected, setSelected] = useState<PersonaName[]>([allPersonas[0], allPersonas[allPersonas.length - 1]])

  const toggle = (persona: PersonaName) => {
    setSelected((prev) => {
      if (prev.includes(persona)) return prev.filter((p) => p !== persona)
      if (prev.length >= 2) return [prev[1], persona]
      return [...prev, persona]
    })
  }

  const shown = persona_evaluations.filter((e) => selected.includes(e.persona))

  return (
    <div>
      <PageHeader title="Persona Comparison" subtitle="Select up to two investor personas to compare side by side." />
      <SimulationBanner />

      <div className="flex gap-2 mb-6">
        {allPersonas.map((p) => (
          <button
            key={p}
            onClick={() => toggle(p)}
            className="rounded-full px-4 py-1.5 text-sm font-medium border transition-colors"
            style={{
              borderColor: selected.includes(p) ? 'var(--color-accent)' : 'var(--color-border)',
              background: selected.includes(p) ? 'rgba(79,156,249,0.15)' : 'transparent',
              color: selected.includes(p) ? 'var(--color-accent)' : 'var(--color-text-dim)',
            }}
          >
            {PERSONA_LABELS[p]}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {shown.map((ev) => (
          <Card key={ev.persona}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{PERSONA_LABELS[ev.persona]}</h3>
              {ev.constraint_violations.length > 0 ? (
                <Pill tone="warn">{ev.constraint_violations.length} constraint flag(s)</Pill>
              ) : (
                <Pill tone="good">within constraints</Pill>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <Metric label="Annualized Return" value={`${(ev.annualized_return * 100).toFixed(1)}%`} />
              <Metric label="Annualized Volatility" value={`${(ev.annualized_volatility * 100).toFixed(1)}%`} />
              <Metric label="Sharpe Ratio" value={ev.sharpe_ratio.toFixed(2)} />
              <Metric label="Max Drawdown" value={`${(ev.max_drawdown * 100).toFixed(1)}%`} />
            </div>

            <h4 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-dim)' }}>
              Candidate Allocation
            </h4>
            <div className="space-y-1 mb-4">
              {Object.entries(ev.proposed_weights)
                .sort((a, b) => b[1] - a[1])
                .map(([symbol, weight]) => (
                  <div key={symbol} className="flex items-center gap-2 text-xs">
                    <span className="w-10 shrink-0">{symbol}</span>
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--color-surface-2)' }}>
                      <div className="h-full rounded-full" style={{ width: `${weight * 100}%`, background: 'var(--color-accent)' }} />
                    </div>
                    <span style={{ color: 'var(--color-text-dim)' }}>{(weight * 100).toFixed(0)}%</span>
                  </div>
                ))}
            </div>

            {ev.constraint_violations.length > 0 && (
              <div>
                <h4 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-dim)' }}>
                  Constraint Violations
                </h4>
                <ul className="text-xs space-y-1" style={{ color: 'var(--color-warn)' }}>
                  {ev.constraint_violations.map((v, i) => (
                    <li key={i}>• {v}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
        {label}
      </div>
      <div className="font-medium">{value}</div>
    </div>
  )
}
