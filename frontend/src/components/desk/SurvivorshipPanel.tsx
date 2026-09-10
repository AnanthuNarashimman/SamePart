import type { MatchDetail } from '../../api/types'

// knowledge/10-frontend-plan.md #Reconciliation Desk: survivorship is an open decision
// (09-open-decisions.md #8) — the prototype rule is simple (most-complete wins per field)
// but the display must exist so the merge is never silent about what happened to each field.
export function SurvivorshipPanel({ match }: { match: MatchDetail }) {
  if (match.verdict !== 'same_material') return null

  const keys = Array.from(new Set([...match.a.attributes.map((x) => x.key), ...match.b.attributes.map((x) => x.key)]))
  const aMap = new Map(match.a.attributes.map((x) => [x.key, x]))
  const bMap = new Map(match.b.attributes.map((x) => [x.key, x]))

  const rows = keys
    .map((key) => {
      const a = aMap.get(key)
      const b = bMap.get(key)
      if (!a || !b) return null
      const winner = a.status === 'extracted' ? 'a' : b.status === 'extracted' ? 'b' : null
      return { key, label: a.label, winner, a, b }
    })
    .filter((r): r is NonNullable<typeof r> => r !== null && r.winner !== null)

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-stone-900">On approve: which value survives</h3>
        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-500">
          rule: most-complete wins
        </span>
      </div>
      <p className="mb-3 text-xs text-stone-400">
        These records merge into one canonical material. Per field, this is the value kept —
        the underlying survivorship rule is deliberately simple for the prototype, not silent.
      </p>
      <ul className="flex flex-col divide-y divide-stone-100">
        {rows.map((r) => (
          <li key={r.key} className="flex items-center justify-between gap-4 py-2 text-sm">
            <span className="text-stone-500">{r.label}</span>
            <span className="font-medium text-stone-900">
              {(r.winner === 'a' ? r.a : r.b).value}
              {(r.winner === 'a' ? r.a : r.b).unit ? ` ${(r.winner === 'a' ? r.a : r.b).unit}` : ''}
              <span className="ml-2 rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700">
                from {r.winner === 'a' ? match.a.org_code : match.b.org_code}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
