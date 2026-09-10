import type { PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'
import { INK, SERIES, STATUS } from './tokens'

// A dot per buyer on one shared scale per row. Identity is carried by the label on each dot,
// not by hue, which is what lets a single series colour do the whole chart.
export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  const items = data.items.slice(0, 7)
  const ceiling = Math.max(...items.map((i) => i.price_max), 1)

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
      <p className="mb-5 text-xs text-stone-400">
        Per base unit, same canonical material. Median spread is {data.median_spread}×. Anything
        past {data.flag_threshold}× is flagged, because a gap that wide more often means a wrong
        merge than a bargain.
      </p>

      <ul className="flex flex-col gap-4">
        {items.map((item) => (
          <li key={item.canonical_id}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3">
              <p className="truncate text-xs text-stone-600" title={item.standardised_short ?? ''}>
                {item.standardised_short ?? item.canonical_id}
              </p>
              <span
                className="shrink-0 font-mono text-[11px] font-medium"
                style={{ color: item.flagged ? STATUS.critical : INK.muted }}
              >
                {item.spread}×{item.flagged ? ' flagged' : ''}
              </span>
            </div>

            <div className="relative h-8">
              {/* The range this row spans, drawn once, so the dots read as a spread. */}
              <div
                className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
                style={{
                  left: `${(item.price_min / ceiling) * 100}%`,
                  width: `${Math.max(((item.price_max - item.price_min) / ceiling) * 100, 0.5)}%`,
                  background: item.flagged ? '#f6dcdc' : '#dbeafe',
                }}
              />
              {item.points.map((p) => (
                <span
                  key={p.org_code}
                  className="absolute top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center"
                  style={{ left: `${Math.min((p.unit_price_base / ceiling) * 100, 99)}%` }}
                  title={`${p.org_code} · ${inr(p.unit_price_base)} per unit · ${p.orders} orders`}
                >
                  {/* 2px surface ring so overlapping marks stay separable. */}
                  <span
                    className="h-2.5 w-2.5 rounded-full ring-2 ring-white"
                    style={{ background: item.flagged ? STATUS.critical : SERIES }}
                  />
                  <span className="ml-1 font-mono text-[10px]" style={{ color: INK.label }}>
                    {p.org_code}
                  </span>
                </span>
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
