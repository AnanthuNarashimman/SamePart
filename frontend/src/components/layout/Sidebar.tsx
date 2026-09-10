import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useOrgs } from '../../api/catalogue'
import { PlatformTourModal } from './PlatformTourModal'

const ICONS = {
  dashboard: (
    <path d="M4 4h6v6H4zM14 4h6v4h-6zM14 12h6v8h-6zM4 14h6v6H4z" />
  ),
  import: (
    <>
      <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </>
  ),
  desk: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </>
  ),
  check: (
    <>
      <path d="M12 3 4.5 6v6c0 4.5 3.2 7.6 7.5 9 4.3-1.4 7.5-4.5 7.5-9V6z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  graph: (
    <>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="12" cy="18" r="2.5" />
      <path d="m8.2 7.3 3 8.7m4.6-8.7-3 8.7M8.5 6h7" />
    </>
  ),
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m15 9-2 6-6 2 2-6z" />
    </>
  ),
} as const

const NAV_ITEMS = [
  { n: '01', label: 'Dashboard', to: '/', icon: 'dashboard' },
  { n: '02', label: 'Import', to: '/import', icon: 'import' },
  { n: '03', label: 'Reconciliation desk', to: '/desk', icon: 'desk' },
  { n: '04', label: 'Duplicate check', to: '/check', icon: 'check' },
  { n: '05', label: 'Relationship graph', to: '/graph', icon: 'graph' },
  { n: '06', label: 'Insights', to: '/insights', icon: 'dashboard' },
] as const

function Icon({ name, className }: { name: keyof typeof ICONS; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ?? 'h-[18px] w-[18px]'}
    >
      {ICONS[name]}
    </svg>
  )
}

const STORAGE_KEY = 'meridian:sidebar-collapsed'

const initials = (code: string) => code.slice(0, 2)

export function Sidebar() {
  const { data: orgs, isLoading, isError } = useOrgs()
  const activeOrg = orgs?.[0]

  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
    } catch {
      // ignore — per-viewer convenience only
    }
  }, [collapsed])

  return (
    <aside
      className={`relative flex h-screen shrink-0 flex-col gap-6 border-r border-stone-200 bg-gradient-to-b from-brand-100 via-brand-400/30 to-brand-50 py-5 text-stone-900 shadow-[1px_0_0_0_rgba(0,0,0,0.02)] transition-[width] duration-300 ease-in-out ${
        collapsed ? 'w-20 px-3' : 'w-72 px-5'
      }`}
    >
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="absolute top-6 -right-3 flex h-6 w-6 items-center justify-center rounded-full border border-stone-200 bg-white text-stone-500 shadow-sm transition-transform hover:text-stone-900"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`h-3 w-3 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
        >
          <path d="m15 6-6 6 6 6" />
        </svg>
      </button>

      <div
        // Full-bleed through the column's padding so the rule divides the whole sidebar.
        // The negative margin has to match the padding exactly and the padding has to match
        // the column's, or the rule overhangs the edge and the mark stops lining up with the
        // nav beneath it — which is why this picks one pair rather than layering two.
        className={`flex items-center gap-2 border-b border-stone-900/10 pt-1 pb-4 ${
          collapsed ? '-mx-3 justify-center px-3' : '-mx-5 px-5'
        }`}
      >
        <img
          src="/logo.png"
          alt="Meridian"
          className={`shrink-0 object-contain ${collapsed ? 'h-11 w-11' : 'h-14 w-14'}`}
        />
        {!collapsed && <span className="text-base font-semibold tracking-wide">Meridian</span>}
      </div>

      {/* The middle scrolls; the tour footer below it does not. On a short window the
          sidebar used to simply run off the bottom of the screen, taking the Start tour
          button with it and leaving no way to reach it — mt-auto cannot help once the
          content is taller than the column. */}
      <div className="scroll-clean -mx-1 flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-1">
      {/* Company context card — which CPSE this session is acting as */}
      {collapsed ? (
        <div className="flex flex-col items-center gap-2 rounded-2xl bg-white p-2 shadow-sm">
          {isLoading && <span className="h-8 w-8 animate-pulse rounded-full bg-stone-100" />}
          {activeOrg && (
            <span
              title={`${activeOrg.name} — acting as reviewer`}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-[10px] font-semibold text-primary-700"
            >
              {initials(activeOrg.code)}
            </span>
          )}
        </div>
      ) : (
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
      )}

      <nav className="flex flex-col gap-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.n}
            to={item.to}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center rounded-xl text-sm font-medium transition-colors ${
                collapsed ? 'justify-center px-0 py-3' : 'justify-between px-4 py-3'
              } ${
                isActive
                  ? 'bg-primary-500 text-white shadow-sm'
                  : 'bg-white/60 text-stone-600 hover:bg-white hover:text-stone-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {collapsed ? (
                  <Icon name={item.icon} className="h-[22px] w-[22px]" />
                ) : (
                  <>
                    <span className="flex items-center gap-3">
                      <Icon name={item.icon} className="h-[18px] w-[18px] shrink-0" />
                      {item.label}
                    </span>
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold ${
                        isActive ? 'bg-white/25 text-white' : 'bg-stone-900/10 text-stone-500'
                      }`}
                    >
                      {item.n}
                    </span>
                  </>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      </div>

      <div className="flex shrink-0 flex-col gap-3">
        {collapsed ? (
          <button
            type="button"
            onClick={() => setTourOpen(true)}
            title="Take a platform tour"
            className="flex h-10 w-full items-center justify-center rounded-lg bg-primary-500 text-white hover:bg-primary-600"
          >
            <Icon name="compass" />
          </button>
        ) : (
          <div className="rounded-2xl bg-white/70 p-4 shadow-sm">
            <div className="mb-1 flex items-center gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-700">
                <Icon name="compass" className="h-3.5 w-3.5" />
              </span>
              <p className="text-sm font-medium text-stone-900">Take a platform tour</p>
            </div>
            <p className="mb-3 text-xs text-stone-500">
              See how import and reconciliation fit together, in under a minute.
            </p>
            <button
              type="button"
              onClick={() => setTourOpen(true)}
              className="block w-full rounded-lg bg-primary-500 py-2 text-center text-sm font-medium text-white hover:bg-primary-600"
            >
              Start tour
            </button>
          </div>
        )}
      </div>

      <PlatformTourModal open={tourOpen} onClose={() => setTourOpen(false)} />
    </aside>
  )
}
