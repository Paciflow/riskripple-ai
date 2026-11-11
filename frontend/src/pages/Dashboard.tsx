import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { DEMO_ANALYSIS } from '../lib/api'
import { DEMO_PORTFOLIO_VALUE } from '../types'
import { Card, PageHeader, Pill, SimulationBanner, StatCard } from '../components/ui'

const COLORS = ['#4f9cf9', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#2dd4bf', '#fb923c']

export default function Dashboard() {
  const { held_portfolio, analysis, report } = DEMO_ANALYSIS
  const allocationData = Object.entries(held_portfolio.weights).map(([symbol, weight]) => ({
    name: symbol,
    value: weight,
  }))

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Fictional $100,000 demo portfolio — overview of current risk and active investigations."
      />
      <SimulationBanner />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Portfolio Value" value={`$${DEMO_PORTFOLIO_VALUE.toLocaleString()}`} />
        <StatCard
          label="Historical Annualized Return"
          value={`${(held_portfolio.annualized_return * 100).toFixed(1)}%`}
          tone="good"
        />
        <StatCard
          label="Annualized Volatility"
          value={`${(held_portfolio.annualized_volatility * 100).toFixed(1)}%`}
          tone="warn"
        />
        <StatCard
          label="Max Drawdown"
          value={`${(held_portfolio.max_drawdown * 100).toFixed(1)}%`}
          tone="bad"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
            Current Allocation
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={allocationData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85}>
                {allocationData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`}
                contentStyle={{ background: 'var(--color-surface-2)', border: 'none', borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {allocationData.map((d, i) => (
              <span key={d.name} className="flex items-center gap-1" style={{ color: 'var(--color-text-dim)' }}>
                <span className="inline-block w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                {d.name} {(d.value * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
            Active Investigation
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <Pill tone={analysis.status === 'complete' ? 'good' : 'warn'}>{analysis.status}</Pill>
            <span className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
              analysis {analysis.analysis_id}
            </span>
          </div>
          <p className="text-sm mb-3">{report.investment_question}</p>
          <div className="text-xs space-y-1" style={{ color: 'var(--color-text-dim)' }}>
            {report.facts.slice(0, 3).map((f, i) => (
              <div key={i}>• {f}</div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
