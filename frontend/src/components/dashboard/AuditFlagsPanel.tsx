import type { AuditFlagResult } from '../../api/types'

// A screening tool, not a proof — 100% precision / 50% recall on the generated data.
// A flagged cluster is worth a look; an unflagged one is not proven correct. See
// BACKEND_FOR_FRONTEND.md /api/analytics/audit-flags.
export function AuditFlagsPanel({ data }: { data: AuditFlagResult }) {
  return (
    <div className="flex h-80 flex-col rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-stone-900">Merges flagged for a second look</h2>
        <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700">
          {data.flagged} flagged
        </span>
      </div>
      <p className="mb-4 shrink-0 text-xs text-stone-400">
        Median price spread across all merges is {data.median_spread_all.toFixed(1)}x; anything past{' '}
        {data.threshold.toFixed(1)}x is surfaced here. Spend data played no part in matching, so this is
        independent evidence — a screening tool, not proof of error.
      </p>
      <ul className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
        {data.items.map((item) => (
          <li key={item.canonical_id} className="rounded-xl bg-violet-50/50 p-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-xs text-stone-500">{item.canonical_id}</span>
              <span className="text-xs font-semibold text-violet-700">{item.price_spread.toFixed(1)}x spread</span>
            </div>
            <p className="mb-1 text-sm font-medium text-stone-800">{item.standardised_short}</p>
            <p className="text-xs text-stone-500">{item.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
