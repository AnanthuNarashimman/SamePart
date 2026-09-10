import type { CascadeBreakdown } from '../../api/types'
import { INK, RAMP, STATUS, count } from './tokens'

// One bar, not four. The question is "what share of the whole never needs a model", and a
// single stacked bar answers that at a glance where four separate bars make you do the
// arithmetic yourself.
export function CascadeChart({ data }: { data: CascadeBreakdown }) {
  const fill = (tier: string, i: number) =>
    tier === 'model' ? STATUS.serious : RAMP[Math.min(i + 1, RAMP.length - 1)]

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">How each pair was decided</h2>
      <p className="mb-5 text-xs text-stone-400">
        {count(data.total_pairs)} candidate pairs, cheapest tier first. A pair only reaches the
        model when the deterministic tiers cannot settle it.
      </p>

      {/* A 2px surface gap between segments, per the mark spec, so adjacent fills stay legible
          without a stroke. */}
      <div className="flex h-11 w-full gap-[2px] overflow-hidden rounded-lg">
        {data.tiers.map((t, i) => (
          <div
            key={t.tier}
            className="group relative first:rounded-l-lg last:rounded-r-lg"
            style={{ width: `${Math.max(t.share * 100, 1.5)}%`, background: fill(t.tier, i) }}
            title={`${t.label}: ${count(t.pairs)} pairs, ${(t.share * 100).toFixed(1)}%`}
          >
            {t.share > 0.12 && (
              <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
                {(t.share * 100).toFixed(0)}%
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Legend is always present for more than one series, and each entry is directly
          labelled with its own value so identity never rests on colour alone. */}
      <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2">
        {data.tiers.map((t, i) => (
          <li key={t.tier} className="flex items-baseline gap-2">
            <span
              className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: fill(t.tier, i) }}
            />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs text-stone-700">{t.label}</span>
              <span className="block font-mono text-[11px]" style={{ color: INK.muted }}>
                {count(t.pairs)} pairs · {(t.share * 100).toFixed(1)}%
              </span>
            </span>
          </li>
        ))}
      </ul>

      <p className="mt-4 border-t border-stone-100 pt-3 text-[11px] leading-relaxed text-stone-400">
        Everything in blue is deterministic: rules a domain engineer can read, running locally at
        no cost. Only the amber slice involves inference, and it is the band the rules could not
        settle.
      </p>
    </div>
  )
}
