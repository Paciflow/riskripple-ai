import { DEMO_ANALYSIS } from '../lib/api'
import { Card, CitationList, PageHeader, SimulationBanner } from '../components/ui'

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="mb-5">
      <h3 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-dim)' }}>
        {title}
      </h3>
      <ul className="space-y-1.5 text-sm">
        {items.map((item, i) => (
          <li key={i}>• {item}</li>
        ))}
      </ul>
    </div>
  )
}

export default function InvestigationReportPage() {
  const { report } = DEMO_ANALYSIS

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.report_id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <PageHeader title="Investigation Report" subtitle={`Report ${report.report_id}`} />
      <SimulationBanner />

      <Card className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold mb-1">{report.investment_question}</h2>
            <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
              {report.event_summary}
            </p>
          </div>
          <button
            onClick={handleExport}
            className="shrink-0 rounded-md px-3 py-1.5 text-xs font-medium border"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-dim)' }}
          >
            Export JSON
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <Section title="Facts (historical data)" items={report.facts} />
          <Section title="Assumptions (hypothetical scenarios)" items={report.assumptions} />
          <Section title="AI Interpretation" items={report.ai_interpretations} />
        </Card>
        <Card>
          <Section title="Known Limitations" items={report.limitations} />
          <Section title="Suggested Next Steps" items={report.next_steps} />
          <div>
            <h3 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-dim)' }}>
              Citations ({report.citations.length})
            </h3>
            <CitationList citations={report.citations} />
          </div>
        </Card>
      </div>
    </div>
  )
}
