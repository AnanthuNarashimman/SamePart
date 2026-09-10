import { NavLink } from 'react-router-dom'
import { useOrgs } from '../../api/catalogue'

const NAV_ITEMS = [
  { n: '01', label: 'Dashboard', to: '/' },
  { n: '02', label: 'Import', to: '/import' },
  { n: '03', label: 'Reconciliation desk', to: '/desk' },
  { n: '04', label: 'Duplicate check', to: '/check' },
  { n: '05', label: 'Relationship graph', to: '/graph' },
]

const initials = (code: string) => code.slice(0, 2)

export function Sidebar() {
  const { data: orgs, isLoading, isError } = useOrgs()
  const activeOrg = orgs?.[0]

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col gap-6 border-r border-stone-200 bg-gradient-to-b from-brand-100 via-brand-400/30 to-brand-50 p-5 text-stone-900 shadow-[1px_0_0_0_rgba(0,0,0,0.02)]">
      <div className="flex items-center gap-2 px-1 pt-1">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-500 text-xs font-bold text-white">
          S
        </span>
        <span className="text-sm font-semibold tracking-wide">SamePart</span>
      </div>

      {/* Company context card — which CPSE this session is acting as */}
      <div className="rounded-2xl bg-white p-4 text-stone-800 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wide text-stone-400">
            Acting as
          </span>
          <span className="rounded-full bg-primary-100 px-2 py-0.5 text-[11px] font-medium text-primary-700">
            Reviewer
          </span>
        </div>
        {isLoading && <p className="text-xs text-stone-400">Loading organisations…</p>}
        {isError && <p className="text-xs text-rose-500">Could not reach the API</p>}
        {activeOrg && (
          <>
            <p className="text-base font-semibold leading-snug">{activeOrg.name}</p>
            <p className="mb-3 text-xs text-stone-400">
              {activeOrg.code} · {activeOrg.record_count} records{activeOrg.simulated ? ' · simulated' : ''}
            </p>
            <div className="flex items-center justify-between border-t border-stone-100 pt-3">
              <div className="flex -space-x-2">
                {orgs.map((org) => (
                  <span
                    key={org.code}
                    title={org.name}
                    className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-stone-100 text-[10px] font-semibold text-stone-600"
                  >
                    {initials(org.code)}
                  </span>
                ))}
              </div>
              <span className="text-[11px] text-stone-400">{orgs.length} CPSEs connected</span>
            </div>
          </>
        )}
      </div>

      <nav className="flex flex-col gap-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.n}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-500 text-white shadow-sm'
                  : 'bg-white/60 text-stone-600 hover:bg-white hover:text-stone-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {item.label}
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
                    isActive ? 'bg-white/25 text-white' : 'bg-stone-900/10 text-stone-500'
                  }`}
                >
                  {item.n}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-3">
        <div className="rounded-2xl bg-white/70 p-4 shadow-sm">
          <p className="text-sm font-medium text-stone-900">Check before creating</p>
          <p className="mb-3 text-xs text-stone-500">
            Stop a new duplicate before a code is minted.
          </p>
          <NavLink
            to="/check"
            className="block w-full rounded-lg bg-primary-500 py-2 text-center text-sm font-medium text-white hover:bg-primary-600"
          >
            Run duplicate check
          </NavLink>
        </div>
      </div>
    </aside>
  )
}
