import type { PriceSpread, PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'
import { STATUS } from './tokens'

// Ported from the barcode-lollipop idiom in lieflat-charts: a hairline field drawn first so
// the shape reads before any value does, tiny marks, and — the part that matters here —
// LABELS ONLY WHERE THEY CANNOT COLLIDE.
//
// My first attempt printed a CPSE code beside every dot, which overlapped the moment two
// buyers paid similar prices. Their answer is not to label everything and hope. It is to
// label the few marks that carry the story and leave the rest to the tooltip. Here that is
// the cheapest and the dearest buyer, anchored to opposite ends, which is also the entire
// point of the row.

const INK = '#1c1917'
const GRID = '#e7e5e4'
const MUTED = '#a8a29e'

function Row({ item, ceiling }: { item: PriceSpread; ceiling: number }) {
  const accent = item.flagged ? STATUS.critical : INK
  const at = (v: number) => Math.min((v / ceiling) * 100, 100)

  const sorted = [...item.points].sort((a, b) => a.unit_price_base - b.unit_price_base)
  const cheapest = sorted[0]
  const dearest = sorted[sorted.length - 1]
  // A label only earns its place if there is room for it. Below a tenth of the row the two
  // ends would overlap, so the dearest keeps its label and the cheapest gives way.
  const roomForBoth = at(dearest.unit_price_base) - at(cheapest.unit_price_base) > 12

  return (
    <li className="pt-1">
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <p className="truncate text-[11px] tracking-tight text-stone-600"
           title={item.standardised_short ?? ''}>
          {item.standardised_short ?? item.canonical_id}
        </p>
        <span className="shrink-0 font-mono text-[10px] font-semibold tracking-tight"
              style={{ color: accent }}>
          {item.spread}×
        </span>
      </div>

      <svg viewBox="0 0 100 16" preserveAspectRatio="none" className="h-9 w-full overflow-visible">
        {/* The field first: a hairline the full width of the scale, so an eye reads the
            position of the marks before it reads any number. */}
        <line x1="0" y1="9" x2="100" y2="9" stroke={GRID} strokeWidth="0.35"
              vectorEffect="non-scaling-stroke" />
        {/* The span this material actually occupies. */}
        <line
          x1={at(cheapest.unit_price_base)} y1="9" x2={at(dearest.unit_price_base)} y2="9"
          stroke={accent} strokeWidth="1" strokeOpacity="0.28"
          vectorEffect="non-scaling-stroke"
        />
        {item.points.map((p) => {
          const isEnd = p === cheapest || p === dearest
          return (
            <g key={p.org_code}>
              {/* A stem down from each mark. Gravity, in their words: it anchors the dot to
                  the field so a cluster still reads as separate marks. */}
              <line
                x1={at(p.unit_price_base)} y1="9" x2={at(p.unit_price_base)} y2="14"
                stroke={accent} strokeWidth={isEnd ? 0.9 : 0.5} strokeOpacity={isEnd ? 0.9 : 0.4}
                vectorEffect="non-scaling-stroke"
              />
              <circle
                cx={at(p.unit_price_base)} cy="9" r={isEnd ? 2.6 : 1.7}
                fill={p === dearest ? accent : '#ffffff'}
                stroke={accent} strokeWidth={p === dearest ? 0 : 1}
                vectorEffect="non-scaling-stroke"
              >
                <title>{`${p.org_code} · ${inr(p.unit_price_base)} per unit · ${p.orders} orders`}</title>
              </circle>
            </g>
          )
        })}
      </svg>

      {/* The two labels that carry the story, anchored to opposite ends so they cannot meet.
          Everything in between is available on hover. */}
      <div className="-mt-1 flex justify-between font-mono text-[10px]">
        <span style={{ color: MUTED }}>
          {roomForBoth && <span className="mr-1 font-semibold" style={{ color: INK }}>{cheapest.org_code}</span>}
          {inr(cheapest.unit_price_base)}
        </span>
        <span style={{ color: MUTED }}>
          <span className="mr-1 font-semibold" style={{ color: accent }}>{dearest.org_code}</span>
          {inr(dearest.unit_price_base)}
        </span>
      </div>
    </li>
  )
}

export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  const items = data.items.slice(0, 7)
  const ceiling = Math.max(...items.map((i) => i.price_max), 1)

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
      <p className="mb-1 text-xs leading-relaxed text-stone-400">
        One line per material, one mark per buyer, all on the same scale. Read the spread before
        the numbers: a wide row means the same bolt costs very different things depending on who
        is buying it.
      </p>
      <p className="mb-5 text-[11px] leading-relaxed text-stone-400">
        Median spread is {data.median_spread}×. Past {data.flag_threshold}× the row turns red,
        because a gap that wide more often means we merged two different materials than that
        somebody found a bargain.
      </p>

      <ul className="flex flex-col gap-2.5">
        {items.map((item) => <Row key={item.canonical_id} item={item} ceiling={ceiling} />)}
      </ul>

      <p className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-stone-100 pt-3
                    font-mono text-[10px] uppercase tracking-wider" style={{ color: MUTED }}>
        <span>● dearest</span>
        <span>○ cheapest</span>
        <span>· other buyers, on hover</span>
      </p>
    </div>
  )
}
