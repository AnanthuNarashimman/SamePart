import type { RationalisationResult } from '../../api/types'

// Capability 5: codes nobody has ordered in four years. See BACKEND_FOR_FRONTEND.md
// /api/analytics/rationalisation.
export function RationalisationPanel({ data }: { data: RationalisationResult }) {
  return (
    <div className="flex h-80 flex-col rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-stone-900">Dead codes</h2>
        <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700">
          {(data.dead_code_rate * 100).toFixed(1)}% of records
        </span>
      </div>
      <p className="mb-4 shrink-0 text-xs text-stone-400">
        Not ordered in the {data.window}, out of {data.records} records. {data.duplicate_codes_removable} more
        codes are removable duplicates once merged into a canonical material.
      </p>
      <ul className="flex min-h-0 flex-1 flex-col divide-y divide-stone-100 overflow-y-auto">
        {data.items.map((item) => (
          <li key={item.record_id} className="flex items-center justify-between gap-4 py-2.5 text-sm">
            <div className="min-w-0">
              <p className="truncate text-stone-700" title={item.raw_description}>{item.raw_description}</p>
              <p className="text-xs text-stone-400">{item.org_code} · {item.source_code}</p>
            </div>
            <span className="shrink-0 rounded-md bg-stone-100 px-2 py-0.5 font-mono text-xs text-stone-500">
              {item.canonical_id}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
