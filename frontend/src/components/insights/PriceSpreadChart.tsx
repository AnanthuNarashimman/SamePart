import type { PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'
import { INK, STATUS, orgColour } from './tokens'
import { HoverCard, useHoverCard } from '../shared/HoverCard'
import { orgOpacity, useOrgFocus } from './OrgFocus'
import { useReveal } from './motion'
import { Pager, usePaged } from '../shared/Paginated'

// One row per material, one dot per buyer, on a shared logarithmic price scale.
//
// Logarithmic because the panel is about a ratio. On a linear scale a row's bar length is
// (max - min), which has almost nothing to do with the spread printed beside it: measured on
// this catalogue, a 1.51x spread on expensive bolts drew 33.8% of the width while a 6.7x
// spread on cheap ones drew 31.3%. The picture contradicted the number. On a log scale the
// length is proportional to log(max/min), so a 2x disagreement is the same length wherever it
// sits on the scale and the bars finally rank the way the numbers do. No axis is drawn, so
// nobody has to think about logarithms — the ends of each bar are labelled in rupees.
//
// The first attempt printed the CPSE code beside every dot, which collided the moment two
// buyers paid similar prices — and buyers paying similar prices is the normal case. Identity
// now comes from colour, assigned once per CPSE and reused on every chart, with a single
// legend above. Nothing is written next to a mark.
//
// The legend is also the page's filter. Focusing one CPSE fades the other buyers here and on
// every other panel at once, which turns "is this buyer consistently the expensive one" from
// a dozen separate reads into a single glance down the column.
export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  // Every row, not just the widest. Slicing to the worst seven meant all seven were past the
  // flag threshold, so the red "flagged" treatment marked every row on screen and therefore
  // distinguished nothing. Showing the unflagged rows too is what gives the flag its meaning,
  // and it also lets a reader see what a normal spread looks like.
  const items = data.items
  const prices = items.flatMap((i) => [i.price_min, i.price_max]).filter((p) => p > 0)
  const lo = Math.log(Math.min(...prices))
  const hi = Math.log(Math.max(...prices))
  const span = hi - lo || 1
  const at = (price: number) => ((Math.log(Math.max(price, 1e-6)) - lo) / span) * 100

  const orgs = Array.from(new Set(items.flatMap((i) => i.points.map((p) => p.org_code)))).sort()
  const shown = useReveal(80)
  const { focus, pinned, hover, toggle, clear } = useOrgFocus()
  const { anchor, show, hide } = useHoverCard()
  const flaggedCount = items.filter((i) => i.flagged).length
  const paged = usePaged(items, 7)

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
        {/* Legend once, at the top. Identity never rests on colour alone because the code is
            written here beside its swatch. A pinned CPSE is filled rather than merely bright,
            so a held filter never looks like the pointer happening to rest somewhere. */}
        <ul className="flex flex-wrap items-center gap-1">
          {orgs.map((o) => {
            const held = pinned && focus === o
            return (
              <li key={o}>
                <button
                  type="button"
                  aria-pressed={held}
                  className="flex items-center gap-1.5 rounded-full px-2 py-1 transition-colors
                             hover:bg-stone-100 focus-visible:outline focus-visible:outline-2
                             focus-visible:outline-offset-1 focus-visible:outline-stone-900"
                  style={{
                    opacity: orgOpacity(o, focus),
                    background: held ? '#1c1917' : undefined,
                  }}
                  onMouseEnter={() => hover(o)}
                  onMouseLeave={() => hover(null)}
                  onFocus={() => hover(o)}
                  onBlur={() => hover(null)}
                  onClick={() => toggle(o)}
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: orgColour(o) }} />
                  <span
                    className="font-mono text-[11px]"
                    style={{ color: held ? '#fff' : INK.label }}
                  >
                    {o}
                  </span>
                </button>
              </li>
            )
          })}
          {pinned && (
            <li>
              <button
                type="button"
                onClick={clear}
                className="rounded-full px-2 py-1 text-[11px] text-stone-500 transition-colors
                           hover:text-stone-900"
              >
                show all ✕
              </button>
            </li>
          )}
        </ul>
      </div>
      <p className="mb-5 text-xs text-stone-400">
        Per base unit, same canonical material, on a shared ratio scale — a wider bar is a wider
        disagreement, whatever the part costs. Median spread is {data.median_spread}×;{' '}
        {flaggedCount} of {items.length} are past {data.flag_threshold}× and marked, because a gap
        that wide more often means a wrong merge than a bargain.
      </p>

      <ul className="flex flex-col gap-3.5">
        {paged.slice.map((item, row) => (
          <li
            key={item.canonical_id}
            className="transition-all duration-500 ease-out motion-reduce:transition-none"
            style={{
              opacity: shown ? 1 : 0,
              transform: shown ? 'none' : 'translateY(6px)',
              transitionDelay: shown ? `${Math.min(row, 8) * 45}ms` : '0ms',
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
                  left: `${at(item.price_min)}%`,
                  width: shown ? `${Math.max(at(item.price_max) - at(item.price_min), 0.6)}%` : '0%',
                  background: item.flagged ? '#f3c9c9' : '#e7e5e4',
                  transitionDelay: shown ? `${Math.min(row, 8) * 45 + 120}ms` : '0ms',
                }}
              />
              {item.points.map((p, i) => {
                const held = pinned && focus === p.org_code
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
                      left: `${Math.min(at(p.unit_price_base), 99.5)}%`,
                      background: orgColour(p.org_code),
                      opacity: shown ? orgOpacity(p.org_code, focus) : 0,
                      // Scaling up on focus rather than only fading keeps the focused buyer
                      // findable even where two dots nearly overlap. A held filter adds a dark
                      // collar on top, so pinned and merely-hovered are told apart at a glance.
                      scale: shown ? (focus === p.org_code ? '1.4' : '1') : '0.2',
                      boxShadow: held ? '0 0 0 2px #1c1917' : undefined,
                      zIndex: focus === p.org_code ? 2 : 1,
                      transitionDelay: shown ? `${Math.min(row, 8) * 45 + 200 + i * 40}ms` : '0ms',
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
            <div className="flex justify-between font-mono text-[10px] tabular-nums"
                 style={{ color: INK.muted }}>
              <span>{inr(item.price_min)}</span>
              <span>{inr(item.price_max)}</span>
            </div>
          </li>
        ))}
      </ul>

      <Pager
        page={paged.page} pages={paged.pages} from={paged.from} to={paged.to}
        total={paged.total} unit="materials" onPage={paged.setPage}
        className="mt-4 border-t border-stone-100 pt-3"
      />

      <HoverCard anchor={anchor} />
    </div>
  )
}
