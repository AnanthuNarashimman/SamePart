import { useState } from 'react'
import type { CascadeBreakdown } from '../../api/types'
import { INK, RAMP, STATUS, count } from './tokens'
import { HoverCard, useHoverCard } from '../shared/HoverCard'
import { useReveal } from './motion'

// One bar, not four. The question is "what share of the whole never needs a model", and a
// single stacked bar answers that at a glance where four separate bars make you do the
// arithmetic yourself.
//
// The bar fills left to right on load, in tier order, which is the order the cascade actually
// runs in — so the animation is the algorithm, not an entrance effect. Hovering a tier dims
// the others and links the bar to its legend row in both directions; clicking holds it, so a
// tier can be studied without the pointer having to stay put.
export function CascadeChart({ data }: { data: CascadeBreakdown }) {
  const shown = useReveal(120)
  const [hovered, setHovered] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)
  const { anchor, show, hide } = useHoverCard()

  const active = pinned ?? hovered
  const fill = (tier: string, i: number) =>
    tier === 'model' ? STATUS.serious : RAMP[Math.min(i + 1, RAMP.length - 1)]
  const opacity = (tier: string) => (active === null || active === tier ? 1 : 0.28)

  const readout = (t: CascadeBreakdown['tiers'][number]) => (
    <>
      <span className="block font-medium text-stone-900">{t.label}</span>
      <span className="mt-0.5 block font-mono text-[11px] text-stone-500">
        {count(t.pairs)} pairs · {(t.share * 100).toFixed(1)}% of {count(data.total_pairs)}
      </span>
      <span className="mt-1 block text-[11px] text-stone-400">
        {t.tier === 'model' ? 'Reached inference' : 'Settled deterministically'}
      </span>
    </>
  )

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div>
          <h2 className="text-sm font-semibold text-stone-900">How each pair was decided</h2>
          <p className="text-xs text-stone-400">
            {count(data.total_pairs)} candidate pairs, cheapest tier first. A pair only reaches
            the model when the deterministic tiers cannot settle it.
          </p>
        </div>
        {pinned && (
          <button
            type="button"
            onClick={() => setPinned(null)}
            className="rounded-full border border-stone-200 px-2.5 py-1 text-[11px] text-stone-500
                       transition-colors hover:border-stone-300 hover:text-stone-700"
          >
            Clear selection
          </button>
        )}
      </div>

      {/* A 2px surface gap between segments, per the mark spec, so adjacent fills stay legible
          without a stroke. */}
      <div
        className="flex h-12 w-full gap-[2px] overflow-hidden rounded-lg"
        onMouseLeave={() => {
          setHovered(null)
          hide()
        }}
      >
        {data.tiers.map((t, i) => (
          <button
            key={t.tier}
            type="button"
            aria-pressed={pinned === t.tier}
            aria-label={`${t.label}: ${count(t.pairs)} pairs, ${(t.share * 100).toFixed(1)} percent`}
            className="relative cursor-pointer first:rounded-l-lg last:rounded-r-lg
                       transition-[width,opacity,filter] duration-700 ease-out
                       focus-visible:outline focus-visible:outline-2
                       focus-visible:outline-offset-2 focus-visible:outline-stone-900
                       motion-reduce:transition-none"
            style={{
              width: shown ? `${Math.max(t.share * 100, 1.5)}%` : '0%',
              background: fill(t.tier, i),
              opacity: opacity(t.tier),
              // Each tier starts filling only once the one before it has, so the bar builds in
              // the order the cascade evaluates.
              transitionDelay: shown ? `${i * 130}ms` : '0ms',
              filter: active === t.tier ? 'saturate(1.15)' : 'none',
            }}
            onMouseEnter={(e) => {
              setHovered(t.tier)
              show(e, readout(t))
            }}
            onMouseMove={(e) => show(e, readout(t))}
            onFocus={() => setHovered(t.tier)}
            onBlur={() => setHovered(null)}
            onClick={() => setPinned((p) => (p === t.tier ? null : t.tier))}
          >
            {t.share > 0.12 && (
              <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
                {(t.share * 100).toFixed(0)}%
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Legend is always present for more than one series, and each entry is directly
          labelled with its own value so identity never rests on colour alone. Each row is a
          control as well as a key: it highlights its own segment on the bar above. */}
      <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        {data.tiers.map((t, i) => (
          <li key={t.tier}>
            <button
              type="button"
              className="flex w-full items-baseline gap-2 rounded-md px-1.5 py-1 text-left
                         transition-colors hover:bg-stone-50 focus-visible:outline
                         focus-visible:outline-2 focus-visible:outline-offset-1
                         focus-visible:outline-stone-900"
              style={{ opacity: opacity(t.tier) }}
              onMouseEnter={() => setHovered(t.tier)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(t.tier)}
              onBlur={() => setHovered(null)}
              onClick={() => setPinned((p) => (p === t.tier ? null : t.tier))}
            >
              <span
                className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: fill(t.tier, i) }}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs text-stone-700">{t.label}</span>
                <span className="block font-mono text-[11px] tabular-nums" style={{ color: INK.muted }}>
                  {count(t.pairs)} pairs · {(t.share * 100).toFixed(1)}%
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>

      <p className="mt-4 border-t border-stone-100 pt-3 text-[11px] leading-relaxed text-stone-400">
        Everything in blue is deterministic: rules a domain engineer can read, running locally at
        no cost. Only the amber slice involves inference, and it is the band the rules could not
        settle.
      </p>

      <HoverCard anchor={anchor} />
    </div>
  )
}
