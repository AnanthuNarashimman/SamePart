import type { RedistributionReport } from '../../api/types'
import { inr } from '../shared/formatters'

const qty = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 0 })

// Stock one CPSE already holds that another is actively buying. Neither can see it today,
// because each describes the item differently and their systems cannot tell they match.
// See BACKEND_FOR_FRONTEND.md /api/analytics/redistribution.
export function RedistributionPanel({ data }: { data: RedistributionReport }) {
  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">Transfer instead of buy</h2>
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700">
          {inr(data.total_avoided_spend)} of purchasing avoided
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        {data.opportunities} materials sitting unissued at one CPSE while another buys them.{' '}
        {qty(data.total_transferable)} units could move. Idle means no goods issue in{' '}
        {data.idle_threshold_days} days.
      </p>

      <ul className="flex flex-col divide-y divide-stone-100">
        {data.items.slice(0, 5).map((item) => {
          const holder = item.holders[0]
          const requester = item.requesters[0]
          return (
            <li key={item.canonical_id} className="py-3">
              <div className="mb-2 flex items-baseline justify-between gap-3">
                <p className="truncate text-sm text-stone-700" title={item.standardised_short ?? ''}>
                  {item.standardised_short ?? item.canonical_id}
                </p>
                <span className="shrink-0 font-mono text-[11px] text-stone-400">
                  {item.national_code}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {holder && (
                  <div className="rounded-lg bg-khaki-50 px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-khaki-700">
                      Holds, unused
                    </p>
                    <p className="text-sm text-stone-700">
                      {holder.org_code} · {qty(holder.stock_on_hand)} {holder.stock_uom}
                      {holder.stock_uom !== 'EA' && (
                        <span className="text-stone-400"> = {qty(holder.stock_base_qty)} each</span>
                      )}
                    </p>
                    <p className="text-xs text-stone-400">
                      {holder.idle_days ? `no issue in ${qty(holder.idle_days)} days` : 'never issued'}
                    </p>
                  </div>
                )}
                {requester && (
                  <div className="rounded-lg bg-stone-50 px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-500">
                      Buys it
                    </p>
                    <p className="text-sm text-stone-700">
                      {requester.org_code} · {qty(requester.annual_demand)}/yr
                    </p>
                    <p className="text-xs text-stone-400">
                      {requester.unit_price_base ? `${inr(requester.unit_price_base)} each · ` : ''}
                      {requester.orders_in_window} orders
                    </p>
                  </div>
                )}
              </div>

              <p className="mt-2 text-xs text-stone-500">
                Transfer <span className="font-medium text-stone-700">{qty(item.transferable)}</span> and
                avoid <span className="font-medium text-stone-700">{inr(item.avoided_spend)}</span>
              </p>
            </li>
          )
        })}
      </ul>

      {/* Caveats belong on the page, not in a tooltip. The figure is avoided purchase cost,
          not net saving, and the stock figures in this dataset are simulated. */}
      <ul className="mt-4 space-y-1 border-t border-stone-100 pt-3">
        {data.caveats.map((c) => (
          <li key={c} className="text-[11px] leading-relaxed text-stone-400">
            {c}
          </li>
        ))}
      </ul>
    </div>
  )
}
