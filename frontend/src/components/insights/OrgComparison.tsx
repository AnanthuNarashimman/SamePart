import {
  Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { AnalyticsSummary } from '../../api/types'
import { INK, RAMP, STATUS, TOOLTIP } from './tokens'

// Records are one measure, so they share one ramp; dead codes are a different kind of thing,
// so they take the reserved status colour and are always labelled.
export function OrgComparison({ data }: { data: AnalyticsSummary }) {
  const rows = data.by_org.map((o) => ({
    org: o.org_code,
    mapped: o.mapped_to_canonical,
    pending: Math.max(o.records - o.mapped_to_canonical - o.dead_codes, 0),
    dead: o.dead_codes,
  }))

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Each CPSE&apos;s master</h2>
      <p className="mb-4 text-xs text-stone-400">
        Mapped to a canonical material, still to work through, and codes with no purchase order in
        the window.
      </p>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: -6, right: 8, top: 10, bottom: 0 }} barSize={38}>
            <CartesianGrid stroke={INK.grid} vertical={false} />
            <XAxis dataKey="org" tickLine={false} axisLine={false}
                   tick={{ fontSize: 12, fill: INK.label }} />
            <YAxis tickLine={false} axisLine={false} width={40}
                   tick={{ fontSize: 11, fill: INK.axis }} />
            <Tooltip contentStyle={TOOLTIP} cursor={{ fill: '#faf9f7' }} />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} iconType="square" iconSize={9} />
            <Bar dataKey="mapped" name="Mapped" stackId="a" fill={RAMP[3]} />
            <Bar dataKey="pending" name="Still to review" stackId="a" fill={RAMP[0]} />
            <Bar dataKey="dead" name="Dead codes" stackId="a" fill={STATUS.critical}
                 radius={[5, 5, 0, 0]}>
              {/* The contrast warning on the light ramp step obligates a visible label; this
                  is that label, and it also happens to be the number people look for. */}
              <LabelList dataKey="dead" position="top"
                         style={{ fontSize: 10, fill: STATUS.critical, fontWeight: 500 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
