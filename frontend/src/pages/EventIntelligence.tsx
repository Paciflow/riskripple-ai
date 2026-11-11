import { DEMO_ANALYSIS } from '../lib/api'
import { Card, CitationList, PageHeader, Pill, SimulationBanner } from '../components/ui'

export default function EventIntelligence() {
  const { report, analysis } = DEMO_ANALYSIS

  return (
    <div>
      <PageHeader title="Event Intelligence" subtitle="Regulatory and geopolitical events relevant to the demo universe." />
      <SimulationBanner />

      <Card className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">{report.event_summary}</h2>
          <Pill tone="warn">simulated event</Pill>
        </div>
        <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
          Jurisdiction: United States (export administration regulations) · Sector: Semiconductors
        </p>
        <p className="mt-3 text-sm">{report.investment_question}</p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
            Facts (from real historical data)
          </h3>
          <ul className="space-y-2 text-sm">
            {report.facts.map((f, i) => (
              <li key={i}>• {f}</li>
            ))}
          </ul>
        </Card>

        <Card>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
            AI Interpretation
          </h3>
          <ul className="space-y-2 text-sm" style={{ color: 'var(--color-text-dim)' }}>
            {report.ai_interpretations.map((f, i) => (
              <li key={i}>• {f}</li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-6">
        <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
          Sources ({analysis.evidence_citations.length})
        </h3>
        <CitationList citations={analysis.evidence_citations} />
      </Card>
    </div>
  )
}
