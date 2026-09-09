import type { CurvePoint } from '../../api/types'
import { pct } from '../shared/formatters'

// The diminishing-returns curve — exists so a data owner stops early on purpose rather
// than feeling obliged to empty the queue. Must be shown, per BACKEND_FOR_FRONTEND.md.
export function Curve({ curve }: { curve: CurvePoint[] }) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <h3 className="mb-1 text-sm font-semibold text-stone-900">Diminishing returns</h3>
      <p className="mb-4 text-xs text-stone-400">
        Each answer clears every pair it unblocks — a small number of records covers most of
        the queue. Stopping early is a legitimate choice, not an unfinished one.
      </p>
      <div className="flex flex-col gap-2">
        {curve.map((c) => (
          <div key={c.questions_answered} className="flex items-center gap-3 text-xs">
            <span className="w-20 shrink-0 text-stone-500">{c.questions_answered} answered</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
              <div className="h-full rounded-full bg-orange-500" style={{ width: pct(c.share_cleared) }} />
            </div>
            <span className="w-28 shrink-0 text-right font-medium text-stone-700">
              {c.pairs_cleared} cleared ({pct(c.share_cleared)})
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
