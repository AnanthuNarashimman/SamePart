import type { SavingsResult } from '../../api/types'

const currency = (n: number, ccy: string) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: ccy, maximumFractionDigits: 0 }).format(n)

export function SavingsPanel({ savings }: { savings: SavingsResult }) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-stone-900">Demand aggregation opportunity</h2>
        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
          base-unit normalised
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        Spend above the lowest observed unit price, once identity clusters are formed
      </p>

      <div className="mb-5 flex flex-wrap items-baseline gap-4">
        <p className="text-3xl font-semibold text-stone-900">
          {currency(savings.total_opportunity, savings.currency)}
        </p>
        {savings.excluded_flagged_clusters > 0 && (
          <p className="text-xs text-stone-400">
            + {currency(savings.excluded_opportunity, savings.currency)} withheld from{' '}
            {savings.excluded_flagged_clusters} flagged clusters under audit — not claimed
          </p>
        )}
      </div>

      <ul className="flex flex-col divide-y divide-stone-100">
        {savings.clusters.map((c) => (
          <li key={c.canonical_id} className="flex items-center justify-between gap-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-stone-800">{c.standardised_short}</p>
              <p className="text-xs text-stone-400">
                {c.canonical_id} · {c.orgs.join(', ')} · {c.total_quantity.toLocaleString('en-IN')} units
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-sm font-semibold text-stone-900">
                {currency(c.aggregation_opportunity, savings.currency)}
              </p>
              <p className="text-xs text-stone-400">
                {currency(c.price_min, savings.currency)}&ndash;{currency(c.price_max, savings.currency)}
                {' '}· {c.spread_pct.toFixed(1)}% spread
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
