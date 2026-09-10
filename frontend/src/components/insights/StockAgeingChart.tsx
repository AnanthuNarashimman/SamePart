import { useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { StockAgeing } from '../../api/types'
import { INK, RAMP, TOOLTIP, compact } from './tokens'
import { chartMotion, usePrefersReducedMotion } from './motion'

// Ordered buckets, so the ramp runs light to dark with age. Nothing here is categorical: the
// darkness IS the message.
//
// Hovering a bucket fades the rest and rewrites the line beneath the chart to that bucket's
// own numbers, so the caption is a readout rather than a fixed sentence. The bars grow from
// the axis on load, in bucket order, which walks the eye left to right into the idle end.
export function StockAgeingChart({ data }: { data: StockAgeing }) {
  const reduced = usePrefersReducedMotion()
  const [active, setActive] = useState<number | null>(null)

  const rows = data.buckets.map((b, i) => ({
    label: b.label,
    units: Math.round(b.base_quantity),
    records: b.records,
    fill: RAMP[Math.min(i, RAMP.length - 1)],
    idle: b.from_days >= data.idle_threshold_days,
  }))
  const idleUnits = rows.filter((r) => r.idle).reduce((a, r) => a + r.units, 0)
  const hovered = active === null ? null : rows[active]

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">How long stock has sat</h2>
      <p className="mb-4 text-xs text-stone-400">
        Base units on hand by time since the last goods issue, across{' '}
        {data.total_records_with_stock} records holding stock.
      </p>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            margin={{ left: -6, right: 8, top: 16, bottom: 0 }}
            barSize={42}
            onMouseLeave={() => setActive(null)}
          >
            <CartesianGrid stroke={INK.grid} vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false}
                   tick={{ fontSize: 10, fill: INK.label }} interval={0} />
            <YAxis tickLine={false} axisLine={false} width={40}
                   tick={{ fontSize: 11, fill: INK.axis }} tickFormatter={compact} />
            <Tooltip
              cursor={{ fill: '#faf9f7' }}
              contentStyle={TOOLTIP}
              formatter={(v, _n, p) => [
                `${Number(v).toLocaleString('en-IN')} units · ${p?.payload?.records ?? 0} records`,
                '',
              ]}
            />
            <Bar
              dataKey="units"
              radius={[5, 5, 0, 0]}
              {...chartMotion(reduced)}
              onMouseEnter={(_entry: unknown, index: number) => setActive(index)}
            >
              {rows.map((r, i) => (
                <Cell
                  key={r.label}
                  fill={r.fill}
                  fillOpacity={active === null || active === i ? 1 : 0.3}
                />
              ))}
              <LabelList dataKey="units" position="top" formatter={(v) => compact(Number(v))}
                         style={{ fontSize: 10, fill: INK.muted }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 border-t border-stone-100 pt-3 text-xs text-stone-500">
        {hovered ? (
          <>
            <span className="font-medium text-stone-800">
              {hovered.units.toLocaleString('en-IN')} units
            </span>{' '}
            across {hovered.records} records last moved {hovered.label.toLowerCase()} ago
            {hovered.idle ? '. Redistribution candidates.' : '.'}
          </>
        ) : (
          <>
            <span className="font-medium text-stone-800">
              {idleUnits.toLocaleString('en-IN')} units
            </span>{' '}
            have not moved in over a year. Those are the redistribution candidates.
          </>
        )}
      </p>
    </div>
  )
}
