import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DEMO_ANALYSIS } from '../lib/api'
import { PERSONA_LABELS, type PersonaName } from '../types'
import { Card, PageHeader, SimulationBanner } from '../components/ui'

const SCENARIO_ORDER = ['mild', 'moderate', 'severe']
const PERSONA_COLORS: Record<PersonaName, string> = {
  prudent: '#34d399',
  equilibre: '#4f9cf9',
  audacieux: '#f87171',
}

export default function ScenarioSimulator() {
  const { persona_evaluations } = DEMO_ANALYSIS.analysis

  const chartData = SCENARIO_ORDER.map((scenario) => {
    const row: Record<string, number | string> = { scenario }
    for (const ev of persona_evaluations) {
      row[ev.persona] = ev.scenario_pnl[scenario] ?? 0
    }
    return row
  })

  return (
    <div>
      <PageHeader
        title="Scenario Simulator"
        subtitle="Hypothetical asset shocks applied to each persona's own candidate allocation — assumptions, not forecasts."
      />
      <SimulationBanner />

      <Card>
        <h3 className="text-sm font-medium mb-4" style={{ color: 'var(--color-text-dim)' }}>
          Portfolio P&amp;L on $100,000 by scenario
        </h3>
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis dataKey="scenario" stroke="var(--color-text-dim)" fontSize={12} />
            <YAxis stroke="var(--color-text-dim)" fontSize={12} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              formatter={(v) => `$${Number(v).toLocaleString()}`}
              contentStyle={{ background: 'var(--color-surface-2)', border: 'none', borderRadius: 8 }}
            />
            <Legend formatter={(v) => PERSONA_LABELS[v as PersonaName] ?? v} />
            {persona_evaluations.map((ev) => (
              <Bar key={ev.persona} dataKey={ev.persona} fill={PERSONA_COLORS[ev.persona]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="mt-6 rounded-lg border px-4 py-3 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-dim)' }}>
        Mild / moderate / severe shocks are illustrative assumptions configured for this
        demo (see backend/src/riskripple/finance/stress.py), not a model prediction of
        actual market response to the simulated event.
      </div>
    </div>
  )
}
