import type { PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'
import { INK, STATUS, orgColour } from './tokens'
import { HoverCard, useHoverCard } from './HoverCard'
import { orgOpacity, useOrgFocus } from './OrgFocus'
import { useReveal } from './motion'

// One row per material, one dot per buyer, on a shared scale.
//
// The first attempt printed the CPSE code beside every dot, which collided the moment two
// buyers paid similar prices — and buyers paying similar prices is the normal case. Identity
// now comes from colour, assigned once per CPSE and reused on every chart, with a single
// legend above. Nothing is written next to a mark.
//
// The legend is also the page's filter. Focusing one CPSE fades the other buyers here and on
// every other panel at once, which turns "is this buyer consistently the expensive one" from
// seven separate reads into a single glance down the column.
export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  const items = data.items.slice(0, 7)
  const ceiling = Math.max(...items.map((i) => i.price_max), 1)
  const orgs = Array.from(new Set(items.flatMap((i) => i.points.map((p) => p.org_code)))).sort()
  const shown = useReveal(80)
  const { focus, pinned, hover, toggle, clear } = useOrgFocus()
  const { anchor, show, hide } = useHoverCard()

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
        {/* Legend once, at the top. Identity never rests on colour alone because the code is
            written here beside its swatch. */}
        <ul className="flex flex-wrap items-center gap-1">
          {orgs.map((o) => (
            <li key={o}>
              <button
                type="button"
                aria-pressed={pinned && focus === o ? true : undefined}
                className="flex items-center gap-1.5 rounded-full px-2 py-1 transition-colors
                           hover:bg-stone-50 focus-visible:outline focus-visible:outline-2
                           focus-visible:outline-offset-1 focus-visible:outline-stone-900"
                style={{
                  opacity: orgOpacity(o, focus),
                  background: pinned && focus === o ? '#f5f5f4' : undefined,
                }}
                onMouseEnter={() => hover(o)}
                onMouseLeave={() => hover(null)}
                onFocus={() => hover(o)}
                onBlur={() => hover(null)}
                onClick={() => toggle(o)}
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: orgColour(o) }} />
                <span className="font-mono text-[11px]" style={{ color: INK.label }}>{o}</span>
              </button>
            </li>
          ))}
          {pinned && (
            <li>
              <button
                type="button"
                onClick={clear}
                className="rounded-full px-2 py-1 text-[11px] text-stone-400 underline
                           underline-offset-2 transition-colors hover:text-stone-700"
              >
                all
              </button>
            </li>
          )}
        </ul>
      </div>
      <p className="mb-5 text-xs text-stone-400">
        Per base unit, same canonical material. Median spread is {data.median_spread}×. Past{' '}
        {data.flag_threshold}× the row is flagged, because a gap that wide more often means a
        wrong merge than a bargain.
      </p>

      <ul className="flex flex-col gap-3.5">
        {items.map((item, row) => (
          <li
            key={item.canonical_id}
            className="transition-all duration-500 ease-out motion-reduce:transition-none"
            style={{
              opacity: shown ? 1 : 0,
              transform: shown ? 'none' : 'translateY(6px)',
              transitionDelay: shown ? `${row * 55}ms` : '0ms',
            }}
          >
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <p className="truncate text-xs text-stone-600" title={item.standardised_short ?? ''}>
                {item.standardised_short ?? item.canonical_id}
              </p>
              <span
                className="shrink-0 font-mono text-[11px] font-medium tabular-nums"
                style={{ color: item.flagged ? STATUS.critical : INK.muted }}
              >
                {item.spread}×
              </span>
            </div>

            <div className="relative h-5">
              {/* The range grows out from the cheapest price, so the bar reads as the spread
                  opening up rather than as a shape that was always there. */}
              <div
                className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full
                           transition-[width] duration-700 ease-out motion-reduce:transition-none"
                style={{
                  left: `${(item.price_min / ceiling) * 100}%`,
                  width: shown
                    ? `${Math.max(((item.price_max - item.price_min) / ceiling) * 100, 0.6)}%`
                    : '0%',
                  background: item.flagged ? '#f6dcdc' : '#e7e5e4',
                  transitionDelay: shown ? `${row * 55 + 120}ms` : '0ms',
                }}
              />
              {item.points.map((p, i) => {
                const lit = focus === null || focus === p.org_code
                return (
                  <button
                    key={p.org_code}
                    type="button"
                    aria-label={`${p.org_code} paid ${inr(p.unit_price_base)} per unit`}
                    className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2
                               rounded-full ring-2 ring-white transition-all duration-500 ease-out
                               focus-visible:outline focus-visible:outline-2
                               focus-visible:outline-offset-2 focus-visible:outline-stone-900
                               motion-reduce:transition-none"
                    style={{
                      left: `${Math.min((p.unit_price_base / ceiling) * 100, 99)}%`,
                      background: orgColour(p.org_code),
                      opacity: shown ? orgOpacity(p.org_code, focus) : 0,
                      // Scaling up on focus rather than only fading keeps the focused buyer
                      // findable even where two dots nearly overlap.
                      scale: shown ? (focus === p.org_code ? '1.45' : '1') : '0.2',
                      zIndex: lit ? 2 : 1,
                      transitionDelay: shown ? `${row * 55 + 200 + i * 40}ms` : '0ms',
                    }}
                    onMouseEnter={(e) => {
                      hover(p.org_code)
                      show(e, (
                        <>
                          <span className="block font-medium text-stone-900">{p.org_code}</span>
                          <span className="mt-0.5 block font-mono text-[11px] text-stone-500">
                            {inr(p.unit_price_base)} per unit · {p.orders} orders
                          </span>
                          <span className="mt-1 block text-[11px] text-stone-400">
                            {item.standardised_short ?? item.canonical_id}
                          </span>
                        </>
                      ))
                    }}
                    onMouseLeave={() => {
                      hover(null)
                      hide()
                    }}
                    onFocus={() => hover(p.org_code)}
                    onBlur={() => hover(null)}
                    onClick={() => toggle(p.org_code)}
                  />
                )
              })}
            </div>
            <div className="flex justify-between font-mono text-[10px] tabular-nums" style={{ color: INK.muted }}>
              <span>{inr(item.price_min)}</span>
              <span>{inr(item.price_max)}</span>
            </div>
          </li>
        ))}
      </ul>

      <HoverCard anchor={anchor} />
    </div>
  )
}
