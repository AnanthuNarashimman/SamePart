import type { PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'
import { INK, STATUS, orgColour } from './tokens'

// One row per material, one dot per buyer, on a shared scale.
//
// The first attempt printed the CPSE code beside every dot, which collided the moment two
// buyers paid similar prices — and buyers paying similar prices is the normal case. Identity
// now comes from colour, assigned once per CPSE and reused on every chart, with a single
// legend above. Nothing is written next to a mark.
export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  const items = data.items.slice(0, 7)
  const ceiling = Math.max(...items.map((i) => i.price_max), 1)
  const orgs = Array.from(new Set(items.flatMap((i) => i.points.map((p) => p.org_code)))).sort()

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
        {/* Legend once, at the top. Identity never rests on colour alone because the code is
            written here beside its swatch. */}
        <ul className="flex flex-wrap items-center gap-3">
          {orgs.map((o) => (
            <li key={o} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: orgColour(o) }} />
              <span className="font-mono text-[11px]" style={{ color: INK.label }}>{o}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="mb-5 text-xs text-stone-400">
        Per base unit, same canonical material. Median spread is {data.median_spread}×. Past{' '}
        {data.flag_threshold}× the row is flagged, because a gap that wide more often means a
        wrong merge than a bargain.
      </p>

      <ul className="flex flex-col gap-3.5">
        {items.map((item) => (
          <li key={item.canonical_id}>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <p className="truncate text-xs text-stone-600" title={item.standardised_short ?? ''}>
                {item.standardised_short ?? item.canonical_id}
              </p>
              <span
                className="shrink-0 font-mono text-[11px] font-medium"
                style={{ color: item.flagged ? STATUS.critical : INK.muted }}
              >
                {item.spread}×
              </span>
            </div>

            <div className="relative h-5">
              <div
                className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
                style={{
                  left: `${(item.price_min / ceiling) * 100}%`,
                  width: `${Math.max(((item.price_max - item.price_min) / ceiling) * 100, 0.6)}%`,
                  background: item.flagged ? '#f6dcdc' : '#e7e5e4',
                }}
              />
              {item.points.map((p) => (
                <span
                  key={p.org_code}
                  className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white"
                  style={{
                    left: `${Math.min((p.unit_price_base / ceiling) * 100, 99)}%`,
                    background: orgColour(p.org_code),
                  }}
                  title={`${p.org_code} · ${inr(p.unit_price_base)} per unit · ${p.orders} orders`}
                />
              ))}
            </div>
            <div className="flex justify-between font-mono text-[10px]" style={{ color: INK.muted }}>
              <span>{inr(item.price_min)}</span>
              <span>{inr(item.price_max)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
