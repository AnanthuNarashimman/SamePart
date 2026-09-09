import type { QueueCounts } from '../../api/types'

const GROUPS: { key: keyof QueueCounts; label: string; hint: string; bar: string; dot: string }[] = [
  { key: 'needs_input', label: 'Needs input', hint: 'Insufficient evidence — asking a question', bar: 'bg-rose-400', dot: 'bg-rose-500' },
  { key: 'possible_alternative', label: 'Possible alternatives', hint: 'Substitutes, identities stay separate', bar: 'bg-amber-300', dot: 'bg-amber-400' },
  { key: 'same_material', label: 'Confirmed matches', hint: 'Ready for a quick approve pass', bar: 'bg-emerald-300', dot: 'bg-emerald-500' },
  { key: 'different', label: 'Confirmed different', hint: 'Low priority, informational', bar: 'bg-stone-200', dot: 'bg-stone-400' },
]

export function QueueBreakdown({ counts }: { counts: QueueCounts }) {
  const total = counts.needs_input + counts.possible_alternative + counts.same_material + counts.different

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-stone-900">Reconciliation queue</h2>
        <span className="text-xs text-stone-400">{total} pending pairs</span>
      </div>

      <div className="mb-4 flex h-2 overflow-hidden rounded-full bg-stone-100">
        {GROUPS.map((g) => (
          <div
            key={g.key}
            className={g.bar}
            style={{ width: total ? `${(counts[g.key] / total) * 100}%` : 0 }}
          />
        ))}
      </div>

      <ul className="flex flex-col gap-3">
        {GROUPS.map((g) => (
          <li key={g.key} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 text-stone-600">
              <span className={`h-2 w-2 rounded-full ${g.dot}`} />
              {g.label}
              <span className="hidden text-xs text-stone-300 sm:inline">· {g.hint}</span>
            </span>
            <span className="font-semibold text-stone-900">{counts[g.key]}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
