import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AnalyticsSummary } from '../../api/types'

// Every organisation looks for its own row first, which is exactly why this is worth showing
// per CPSE rather than as one national average.
export function OrgComparison({ data }: { data: AnalyticsSummary }) {
  const rows = data.by_org.map((o) => ({
    org: o.org_code,
    mapped: o.mapped_to_canonical,
    dead: o.dead_codes,
    other: Math.max(o.records - o.mapped_to_canonical - o.dead_codes, 0),
  }))
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <h2 className="mb-1 text-sm font-semibold text-stone-900">Each CPSE&apos;s master</h2>
      <p className="mb-4 text-xs text-stone-400">
        Records mapped to a canonical material, codes with no purchase order in the window, and the
        rest still to work through.
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="#f5f5f4" vertical={false} />
            <XAxis dataKey="org" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#57534e' }} />
            <YAxis tickLine={false} axisLine={false} width={38} tick={{ fontSize: 11, fill: '#a8a29e' }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e7e5e4' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="mapped" name="Mapped" stackId="a" fill="#84cc16" radius={[0, 0, 0, 0]} />
            <Bar dataKey="other" name="Not yet mapped" stackId="a" fill="#e7e5e4" />
            <Bar dataKey="dead" name="Dead codes" stackId="a" fill="#fda4af" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
