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

  // Starting the area at the origin, because nobody has answered nothing and cleared 3%.
  const rows = [
    { answered: 0, cleared: 0 },
    ...data.curve.map((c) => ({
      answered: c.questions_answered,
      cleared: Math.round(c.share_cleared * 1000) / 10,
    })),
  ]
  const half = rows.find((r) => r.cleared >= 50)
  const end = rows[rows.length - 1]
  const probe = at === null ? null : rows[at]

  // Five ticks ending exactly on the queue length, so the axis names the number the caption
  // talks about rather than stopping at a round number short of it.
  const ticks = Array.from({ length: 5 }, (_, i) => Math.round((data.questions * i) / 4))

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
            {/* A number axis, not a category one. Recharts defaults an XAxis with a dataKey to
                categories, which spaces every sample equally: with the curve sampled at 10,
                25, 50, 100 and 168 answers, gaps of 10 and 68 were drawn the same width and
                the diminishing-returns bend — the entire point of the panel — was flattened
                into something close to a straight line. */}
            <XAxis
              dataKey="answered" type="number" domain={[0, data.questions]} ticks={ticks}
              tickLine={false} axisLine={false} allowDecimals={false}
              tick={{ fontSize: 11, fill: INK.axis }}
            />
            <YAxis
              tickLine={false} axisLine={false} width={48} domain={[0, 100]}
              tick={{ fontSize: 11, fill: INK.axis }} tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              separator=""
              formatter={(v) => [`${v}% of the queue cleared`, '']}
              labelFormatter={(l) => `${l} answers`}
              contentStyle={TOOLTIP}
              cursor={{ stroke: '#d6d3d1', strokeWidth: 1 }}
            />
            {half && <ReferenceLine y={50} stroke="#e7e5e4" strokeDasharray="4 4" />}
            <Area
              type="monotone" dataKey="cleared" stroke={SERIES} strokeWidth={2}
              fill="url(#stopFill)"
              // One dot per answer would be 168 of them. The curve is the mark now; the
              // active dot is what the pointer needs.
              dot={false}
              activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
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
          // Stated from the curve rather than from a checkpoint. This sentence used to read
          // "50 answers clear half the queue. The last 118 clear the other half." Both halves
          // were false: the curve was sampled at only five points, so the first sample past
          // 50% was 50 answers, which actually clears 74%; and answering all of them reaches
          // 97%, not 100%, so there is no "other half" to clear.
          <>
            <span className="font-medium text-stone-800 tabular-nums">
              {half.answered} answers
            </span>{' '}
            clear half the queue. All {data.questions} clear{' '}
            <span className="tabular-nums">{end.cleared}%</span> — the last{' '}
            {data.questions - half.answered} are worth{' '}
            <span className="tabular-nums">{Math.round((end.cleared - half.cleared) * 10) / 10}%</span>{' '}
            between them.
          </>
        ) : null}
      </p>
    </div>
  )
}
