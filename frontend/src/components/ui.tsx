import type { CSSProperties, ReactNode } from 'react'

export function Card({
  children,
  className = '',
  style,
}: {
  children: ReactNode
  className?: string
  style?: CSSProperties
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${className}`}
      style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', ...style }}
    >
      {children}
    </div>
  )
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {subtitle && (
        <p className="mt-1 text-sm" style={{ color: 'var(--color-text-dim)' }}>
          {subtitle}
        </p>
      )}
    </div>
  )
}

export function StatCard({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string
  value: string
  tone?: 'neutral' | 'good' | 'bad' | 'warn'
  hint?: string
}) {
  const color =
    tone === 'good'
      ? 'var(--color-good)'
      : tone === 'bad'
        ? 'var(--color-bad)'
        : tone === 'warn'
          ? 'var(--color-warn)'
          : 'var(--color-text)'
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-dim)' }}>
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold" style={{ color }}>
        {value}
      </div>
      {hint && (
        <div className="mt-1 text-xs" style={{ color: 'var(--color-text-dim)' }}>
          {hint}
        </div>
      )}
    </Card>
  )
}

export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'bad' | 'warn' }) {
  const bg =
    tone === 'good'
      ? 'rgba(52,211,153,0.15)'
      : tone === 'bad'
        ? 'rgba(248,113,113,0.15)'
        : tone === 'warn'
          ? 'rgba(251,191,36,0.15)'
          : 'rgba(147,161,189,0.15)'
  const color =
    tone === 'good'
      ? 'var(--color-good)'
      : tone === 'bad'
        ? 'var(--color-bad)'
        : tone === 'warn'
          ? 'var(--color-warn)'
          : 'var(--color-text-dim)'
  return (
    <span className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: bg, color }}>
      {children}
    </span>
  )
}

export function SimulationBanner() {
  return (
    <div
      className="mb-6 rounded-lg border px-4 py-3 text-sm"
      style={{ borderColor: 'var(--color-warn)', background: 'rgba(251,191,36,0.08)', color: 'var(--color-warn)' }}
    >
      Fictional $100,000 demo portfolio and simulated event. Simulation only — no real
      transactions, and this is not personalized financial advice.
    </div>
  )
}

export function CitationList({ citations }: { citations: { source_name: string; observation_date: string | null; publication_date: string | null; source_url: string }[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {citations.map((c, i) => (
        <li key={i} className="flex items-start gap-2">
          <span className="mt-0.5 shrink-0 rounded px-1.5 text-xs" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-dim)' }}>
            {i + 1}
          </span>
          <div>
            <a href={c.source_url} target="_blank" rel="noreferrer" className="hover:underline" style={{ color: 'var(--color-accent)' }}>
              {c.source_name}
            </a>
            <span style={{ color: 'var(--color-text-dim)' }}>
              {' '}
              — as of {c.observation_date || c.publication_date || 'n/a'}
            </span>
          </div>
        </li>
      ))}
    </ul>
  )
}
