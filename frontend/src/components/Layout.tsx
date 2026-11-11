import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/events', label: 'Event Intelligence' },
  { to: '/portfolio', label: 'Portfolio Analyzer' },
  { to: '/graph', label: 'Ripple Graph' },
  { to: '/scenarios', label: 'Scenario Simulator' },
  { to: '/personas', label: 'Persona Comparison' },
  { to: '/report', label: 'Investigation Report' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen" style={{ background: 'var(--color-bg)' }}>
      <aside
        className="w-60 shrink-0 border-r p-4 flex flex-col gap-1"
        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
      >
        <div className="px-2 py-3 mb-2">
          <div className="text-lg font-semibold tracking-tight">RiskRipple AI</div>
          <div className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
            From global events to smarter decisions
          </div>
        </div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm transition-colors ${
                isActive ? 'font-medium' : 'hover:bg-white/5'
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? 'var(--color-surface-2)' : 'transparent',
              color: isActive ? 'var(--color-text)' : 'var(--color-text-dim)',
            })}
          >
            {item.label}
          </NavLink>
        ))}
        <div className="mt-auto px-2 pt-4 text-[11px] leading-snug" style={{ color: 'var(--color-text-dim)' }}>
          Simulation only. No real transactions. Not personalized financial advice.
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
