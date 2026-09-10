import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { QuestionPage } from '../../api/types'

// Diminishing returns on answering the queue. This exists so a data owner stops early on
// purpose rather than feeling obliged to empty it, which is a decision the chart makes
// visible and a table does not.
export function StoppingCurve({ data }: { data: QuestionPage }) {
  const rows = data.curve.map((c) => ({
    answered: c.questions_answered,
    cleared: Math.round(c.share_cleared * 1000) / 10,
  }))
  const half = rows.find((r) => r.cleared >= 50)
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">Where to stop answering</h2>
        <span className="rounded-full bg-khaki-50 px-2 py-0.5 text-[11px] font-medium text-khaki-700">
          {data.records} records to open
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        {data.pairs_deferred.toLocaleString('en-IN')} deferred pairs are {data.questions} blanks across{' '}
        {data.records} records. Answered highest-value first,{' '}
        {half ? `${half.answered} answers clear half the queue.` : 'returns fall away quickly.'}
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ left: 0, right: 12, top: 8, bottom: 4 }}>
            <CartesianGrid stroke="#f5f5f4" vertical={false} />
            <XAxis
              dataKey="answered"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#a8a29e' }}
              label={{ value: 'questions answered', position: 'insideBottom', offset: -2, fontSize: 10, fill: '#a8a29e' }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={38}
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: '#a8a29e' }}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              formatter={(v) => [`${v}% of the queue cleared`, '']}
              labelFormatter={(l) => `${l} answers`}
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e7e5e4' }}
            />
            {half && <ReferenceLine y={50} stroke="#d6d3d1" strokeDasharray="3 3" />}
            <Line type="monotone" dataKey="cleared" stroke="#84cc16" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
