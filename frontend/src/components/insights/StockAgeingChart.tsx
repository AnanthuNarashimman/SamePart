import { useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { StockAgeing } from '../../api/types'
import { INK, RAMP, TOOLTIP, axisUnit, count } from './tokens'
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
  const fmt = axisUnit(Math.max(...rows.map((r) => r.units), 1))

  // A bucket can legitimately hold nothing, and a zero-height bar draws as absolutely nothing
  // — which reads as a broken chart rather than as an empty bucket. The note has to live on
  // the axis tick rather than on the bar, because a label attached to a bar of zero height
  // does not render at all, which is the failure being fixed.
  const BucketTick = ({ x, y, payload }: { x?: number; y?: number; payload?: { value?: string } }) => {
    const label = String(payload?.value ?? '')
    const empty = rows.find((r) => r.label === label)?.units === 0
    return (
      <g transform={`translate(${x ?? 0},${y ?? 0})`}>
        <text x={0} y={12} textAnchor="middle" fontSize={10} fill={INK.label}>{label}</text>
        {empty && (
          <text x={0} y={25} textAnchor="middle" fontSize={9} fill={INK.muted} fontStyle="italic">
            none on hand
          </text>
        )}
      </g>
    )
  }

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
            margin={{ left: -4, right: 8, top: 18, bottom: 0 }}
            barSize={42}
            // The band, not the bar. Recharts fires a bar's own mouse events only over the
            // drawn rectangle, so the two shortest buckets here — a few pixels tall — showed a
            // tooltip while the caption and the highlight stayed on the previous bucket. The
            // chart-level index follows the category band the tooltip already uses, so all
            // three now agree.
            onMouseMove={(st) => {
              const i = Number(st?.activeTooltipIndex)
              setActive(Number.isInteger(i) && i >= 0 && i < rows.length ? i : null)
            }}
            onMouseLeave={() => setActive(null)}
          >
            <CartesianGrid stroke={INK.grid} vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0}
                   height={34} tick={<BucketTick />} />
            <YAxis tickLine={false} axisLine={false} width={52}
                   tick={{ fontSize: 11, fill: INK.axis }} tickFormatter={fmt} />
            <Tooltip
              cursor={{ fill: '#faf9f7' }}
              contentStyle={TOOLTIP}
              // Recharts joins name and value with " : ", so an empty name left every tooltip
              // opening with a stray colon.
              separator=""
              formatter={(v, _n, p) => [
                Number(v) === 0
                  ? 'no stock in this bucket'
                  : `${count(Number(v))} units · ${p?.payload?.records ?? 0} records`,
                '',
              ]}
            />
            <Bar
              dataKey="units"
              radius={[5, 5, 0, 0]}
              {...chartMotion(reduced)}
            >
              {rows.map((r, i) => (
                <Cell
                  key={r.label}
                  fill={r.fill}
                  fillOpacity={active === null || active === i ? 1 : 0.3}
                />
              ))}
              <LabelList
                dataKey="units" position="top" offset={6}
                style={{ fontSize: 10, fill: INK.label }}
                formatter={(v) => (Number(v) === 0 ? '' : fmt(Number(v)))}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 border-t border-stone-100 pt-3 text-xs text-stone-500">
        {hovered ? (
          hovered.units === 0 ? (
            <>
              Nothing on hand last moved{' '}
              <span className="font-medium text-stone-800">{hovered.label.toLowerCase()}</span> ago.
            </>
          ) : (
            <>
              <span className="font-medium text-stone-800 tabular-nums">
                {count(hovered.units)} units
              </span>{' '}
              across {hovered.records} records last moved {hovered.label.toLowerCase()} ago
              {hovered.idle ? '. Redistribution candidates.' : '.'}
            </>
          )
        ) : (
          <>
            <span className="font-medium text-stone-800 tabular-nums">{count(idleUnits)} units</span>{' '}
            have not moved in over a year. Those are the redistribution candidates.
          </>
        )}
      </p>
    </div>
  )
}
