import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { CascadeBreakdown } from '../../api/types'

// The strongest technical claim in the system, as one picture: almost every decision is
// settled before anything reaches a model. Answers "where is the AI" and "does this scale"
// at the same time.
export function CascadeChart({ data }: { data: CascadeBreakdown }) {
  const rows = data.tiers.map((t) => ({
    label: t.label,
    pairs: t.pairs,
    share: t.share,
    model: t.needs_a_model,
  }))
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">How each pair was decided</h2>
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700">
          {(data.share_without_a_model * 100).toFixed(1)}% without a model
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        {data.total_pairs.toLocaleString('en-IN')} candidate pairs, cheapest tier first. A pair only
        reaches the model when the deterministic tiers cannot settle it.
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 56, top: 4, bottom: 4 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="label"
              width={170}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: '#57534e' }}
            />
            <Bar dataKey="pairs" radius={[0, 6, 6, 0]} barSize={26}>
              {rows.map((r) => (
                <Cell key={r.label} fill={r.model ? '#a8a29e' : '#84cc16'} />
              ))}
              <LabelList
                dataKey="pairs"
                position="right"
                formatter={(v) => Number(v).toLocaleString('en-IN')}
                style={{ fontSize: 11, fill: '#78716c' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-[11px] text-stone-400">
        Grey is the model tier. Everything green is deterministic: rules a domain engineer can read,
        which run locally and cost nothing.
      </p>
    </div>
  )
}
