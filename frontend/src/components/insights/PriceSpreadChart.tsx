import type { PriceSpreadReport } from '../../api/types'
import { inr } from '../shared/formatters'

// What each CPSE paid per base unit for the same canonical material. This is the money
// story, and it is also where the audit flags come from: a spread far above the norm is more
// likely to mean a wrong merge than a genuine bargain.
export function PriceSpreadChart({ data }: { data: PriceSpreadReport }) {
  const ceiling = Math.max(...data.items.map((i) => i.price_max), 1)
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">What each CPSE paid</h2>
        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-600">
          median spread {data.median_spread}×
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        Per base unit, same canonical material. Spreads above {data.flag_threshold}× are flagged for
        review, because they more often mean a wrong merge than a bargain.
      </p>
      <ul className="flex flex-col gap-3">
        {data.items.slice(0, 8).map((item) => (
          <li key={item.canonical_id}>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <p className="truncate text-xs text-stone-600" title={item.standardised_short ?? ''}>
                {item.standardised_short ?? item.canonical_id}
              </p>
              <span
                className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  item.flagged ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-500'
                }`}
              >
                {item.spread}× {item.flagged ? 'flagged' : ''}
              </span>
            </div>
            {/* One row, one scale. Every dot is a real price a real buyer paid. */}
            <div className="relative h-7 rounded-md bg-stone-50">
              {item.points.map((p) => (
                <div
                  key={p.org_code}
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${Math.min((p.unit_price_base / ceiling) * 100, 98)}%` }}
                  title={`${p.org_code} · ${inr(p.unit_price_base)} per unit · ${p.orders} orders`}
                >
                  <span className="block rounded-full bg-brand-500 px-1.5 py-0.5 text-[9px] font-medium text-white">
                    {p.org_code}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-0.5 flex justify-between text-[10px] text-stone-400">
              <span>{inr(item.price_min)}</span>
              <span>{inr(item.price_max)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
