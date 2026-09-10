import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { StockAgeing } from '../../api/types'

// How long stock has sat without a goods issue. The right-hand bars are the redistribution
// candidates: material somebody is holding while somebody else buys it.
export function StockAgeingChart({ data }: { data: StockAgeing }) {
  const rows = data.buckets.map((b) => ({
    label: b.label,
    units: Math.round(b.base_quantity),
    records: b.records,
    idle: b.from_days >= data.idle_threshold_days,
  }))
  const idleUnits = rows.filter((r) => r.idle).reduce((a, r) => a + r.units, 0)
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">How long stock has sat</h2>
        <span className="rounded-full bg-khaki-50 px-2 py-0.5 text-[11px] font-medium text-khaki-700">
          {idleUnits.toLocaleString('en-IN')} units idle
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        Base units on hand by time since the last goods issue, across{' '}
        {data.total_records_with_stock} records holding stock. Anything past{' '}
        {data.idle_threshold_days} days is a redistribution candidate.
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="#f5f5f4" vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#57534e' }} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={46}
              tick={{ fontSize: 11, fill: '#a8a29e' }}
              tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)}
            />
            <Tooltip
              formatter={(v, _n, p) => [
                `${Number(v).toLocaleString('en-IN')} units · ${p?.payload?.records ?? 0} records`,
                '',
              ]}
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e7e5e4' }}
            />
            <Bar dataKey="units" radius={[6, 6, 0, 0]} barSize={44}>
              {rows.map((r) => (
                <Cell key={r.label} fill={r.idle ? '#f59e0b' : '#d6d3d1'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
