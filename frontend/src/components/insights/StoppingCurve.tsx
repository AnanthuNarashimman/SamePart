import { useState } from 'react'
import {
  Area, AreaChart, CartesianGrid, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { QuestionPage } from '../../api/types'
import { INK, SERIES, TOOLTIP } from './tokens'
import { chartMotion, usePrefersReducedMotion } from './motion'

// Diminishing returns, with the decision annotated on the plot rather than left for the
// reader to find. The chart exists so a data owner stops early on purpose.
//
// So the interaction is the point of the panel, not an addition to it: moving along the curve
// answers "what happens if I stop here" directly, in the sentence below the plot — how much of
// the queue is cleared, and how many answers it would take to finish the rest. Reading that
// off the axes is arithmetic the reader should not have to do while deciding.
export function StoppingCurve({ data }: { data: QuestionPage }) {
  const reduced = usePrefersReducedMotion()
  const [at, setAt] = useState<number | null>(null)

  const rows = data.curve.map((c) => ({
    answered: c.questions_answered,
    cleared: Math.round(c.share_cleared * 1000) / 10,
  }))
  const half = rows.find((r) => r.cleared >= 50)
  const probe = at === null ? null : rows[at]

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Where to stop answering</h2>
      <p className="mb-4 text-xs text-stone-400">
        {data.pairs_deferred.toLocaleString('en-IN')} deferred pairs are {data.questions} blanks
        across {data.records} records, answered highest-value first.
      </p>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={rows}
            margin={{ left: -6, right: 14, top: 10, bottom: 0 }}
            onMouseMove={(s) => {
              // Recharts 3 widens this index to include null and a string form, so it is
              // coerced rather than trusted.
              const i = Number(s?.activeTooltipIndex)
              setAt(Number.isInteger(i) && i >= 0 && i < rows.length ? i : null)
            }}
            onMouseLeave={() => setAt(null)}
          >
            <defs>
              <linearGradient id="stopFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={SERIES} stopOpacity={0.18} />
                <stop offset="100%" stopColor={SERIES} stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={INK.grid} vertical={false} />
            <XAxis
              dataKey="answered" tickLine={false} axisLine={false}
              tick={{ fontSize: 11, fill: INK.axis }}
            />
            <YAxis
              tickLine={false} axisLine={false} width={40} domain={[0, 100]}
              tick={{ fontSize: 11, fill: INK.axis }} tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v) => [`${v}% of the queue cleared`, '']}
              labelFormatter={(l) => `${l} answers`}
              contentStyle={TOOLTIP}
              cursor={{ stroke: '#d6d3d1', strokeWidth: 1 }}
            />
            {half && <ReferenceLine y={50} stroke="#e7e5e4" strokeDasharray="4 4" />}
            <Area
              type="monotone" dataKey="cleared" stroke={SERIES} strokeWidth={2}
              fill="url(#stopFill)" dot={{ r: 3, fill: SERIES, strokeWidth: 0 }}
              activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
              {...chartMotion(reduced, 200)}
            />
            {half && (
              <ReferenceDot
                x={half.answered} y={half.cleared} r={5}
                fill={SERIES} stroke="#fff" strokeWidth={2}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 border-t border-stone-100 pt-3 text-xs text-stone-500">
        {probe ? (
          <>
            Stopping at{' '}
            <span className="font-medium text-stone-800 tabular-nums">
              {probe.answered} answers
            </span>{' '}
            clears <span className="tabular-nums">{probe.cleared}%</span> of the queue and leaves{' '}
            <span className="tabular-nums">{data.questions - probe.answered}</span> blanks unasked.
          </>
        ) : half ? (
          <>
            <span className="font-medium text-stone-800">{half.answered} answers</span> clear half
            the queue. The last {data.questions - half.answered} clear the other half.
          </>
        ) : null}
      </p>
    </div>
  )
}
