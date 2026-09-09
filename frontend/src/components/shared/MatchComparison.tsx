import type { MatchDetail } from '../../api/types'
import { inr, VERDICT_LABEL, VERDICT_TONE } from './formatters'
import { AttributeRow } from './AttributeRow'

// Shared by the Reconciliation Desk comparison view and the Duplicate-Prevention Check
// result — same fields, same evidence-first layout, per BACKEND_FOR_FRONTEND.md.
export function MatchComparison({ match }: { match: MatchDetail }) {
  const keys = Array.from(new Set([...match.a.attributes.map((x) => x.key), ...match.b.attributes.map((x) => x.key)]))
  const byKey = (attrs: typeof match.a.attributes) => new Map(attrs.map((x) => [x.key, x]))
  const aMap = byKey(match.a.attributes)
  const bMap = byKey(match.b.attributes)

  return (
    <div className="rounded-2xl border border-stone-100 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-4 border-b border-stone-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${VERDICT_TONE[match.verdict]}`}>
            {VERDICT_LABEL[match.verdict]}
          </span>
          <span className="text-xs text-stone-400">
            {match.score != null ? `score ${match.score.toFixed(2)} · ` : ''}decided by {match.decided_by}
          </span>
        </div>
        {match.gate_overrode && (
          <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
            gate overrode score
          </span>
        )}
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_11rem_11rem] gap-3 border-b border-stone-100 px-5 py-4 text-xs">
        <div />
        <RecordHeader record={match.a} />
        <RecordHeader record={match.b} />
      </div>

      <div className="flex flex-col gap-0.5 px-3 py-3">
        {keys.map((key) => {
          const a = aMap.get(key)
          const b = bMap.get(key)
          if (!a || !b) return null
          return <AttributeRow key={key} a={a} b={b} />
        })}
      </div>

      {(match.gate_firings.length > 0 || match.substitution_conditions.length > 0 || match.notes.length > 0) && (
        <div className="flex flex-col gap-3 border-t border-stone-100 px-5 py-4">
          {match.gate_firings.map((g) => (
            <div key={g.gate_id} className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">
              <p className="font-medium">{g.message}</p>
              <p className="mt-1 text-xs text-rose-600">{g.detail}</p>
            </div>
          ))}
          {match.substitution_conditions.map((c, i) => (
            <div key={i} className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
              <p className="text-xs font-medium uppercase tracking-wide text-amber-500">Safe only if</p>
              <p className="mt-1">{c}</p>
            </div>
          ))}
          {match.notes.map((n, i) => (
            <p key={i} className="text-xs text-stone-400">{n}</p>
          ))}
        </div>
      )}
    </div>
  )
}

function RecordHeader({ record }: { record: MatchDetail['a'] }) {
  return (
    <div>
      <p className="font-semibold text-stone-900">{record.org_code}</p>
      <p className="truncate text-stone-400" title={record.source_code}>{record.source_code}</p>
      <p className="mt-1 text-stone-500">
        {record.unit_price_base != null ? `${inr(record.unit_price_base)} / ${record.base_uom ?? '?'}` : 'price unknown'}
      </p>
    </div>
  )
}
