import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { AnalyticsSummary } from '../../api/types'
import { INK, RAMP, STATUS, TOOLTIP } from './tokens'
import { orgOpacity, useOrgFocus } from './OrgFocus'
import { chartMotion, usePrefersReducedMotion } from './motion'

// Records are one measure, so they share one ramp; dead codes are a different kind of thing,
// so they take the reserved status colour and are always labelled.
//
// The bars grow from the axis on load and respond to the page-wide CPSE focus, so selecting a
// buyer in the price panel fades the other four columns here without a second interaction.
// The axis labels are the controls: they are the only place on the page where every CPSE is
// named, which makes them the natural handle for picking one.

// Bars must be declared bottom-of-stack first, but a reader scans a stacked bar from the top
// down, so legend and tooltip are given that order explicitly. Left to their defaults they
// came out as Dead codes, Mapped, Still to review — an order matching neither the stack nor
// each other.
const SERIES = [
  { key: 'mapped', name: 'Mapped', fill: RAMP[3] },
  { key: 'pending', name: 'Still to review', fill: RAMP[0] },
  { key: 'dead', name: 'Dead codes', fill: STATUS.critical },
] as const
const TOP_DOWN = [...SERIES].reverse()

function StackLegend() {
  return (
    <ul className="flex items-center justify-center gap-4 pt-1.5">
      {TOP_DOWN.map((s) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.fill }} />
          <span className="text-[11px]" style={{ color: INK.label }}>{s.name}</span>
        </li>
      ))}
    </ul>
  )
}

export function OrgComparison({ data }: { data: AnalyticsSummary }) {
  const reduced = usePrefersReducedMotion()
  const { focus, pinned, hover, toggle } = useOrgFocus()

  const rows = data.by_org.map((o) => ({
    org: o.org_code,
    mapped: o.mapped_to_canonical,
    pending: Math.max(o.records - o.mapped_to_canonical - o.dead_codes, 0),
    dead: o.dead_codes,
  }))

  // A clickable axis label. Recharts hands the tick its own placement, so the hit target has
  // to be drawn rather than inherited from a wrapper.
  const OrgTick = ({ x, y, payload }: { x?: number; y?: number; payload?: { value?: string } }) => {
    const org = String(payload?.value ?? '')
    const selected = pinned && focus === org
    return (
      <g
        transform={`translate(${x ?? 0},${y ?? 0})`}
        className="cursor-pointer"
        onMouseEnter={() => hover(org)}
        onMouseLeave={() => hover(null)}
        onClick={() => toggle(org)}
      >
        <rect x={-26} y={2} width={52} height={20} rx={10}
              fill={selected ? '#1c1917' : 'transparent'} />
        <text
          x={0} y={16} textAnchor="middle" fontSize={12}
          fill={selected ? '#fff' : focus === null || focus === org ? INK.label : INK.muted}
          fontWeight={selected ? 600 : 400}
        >
          {org}
        </text>
      </g>
    )
  }

  return (
    <div className="flex flex-col rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Each CPSE&apos;s master</h2>
      <p className="mb-4 text-xs text-stone-400">
        Mapped to a canonical material, still to work through, and codes with no purchase order in
        the window. Hover a column to isolate that CPSE across the page; click to hold it.
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            margin={{ left: -6, right: 8, top: 10, bottom: 4 }}
            barSize={38}
            onMouseLeave={() => hover(null)}
          >
            <CartesianGrid stroke={INK.grid} vertical={false} />
            <XAxis dataKey="org" tickLine={false} axisLine={false} height={26} tick={<OrgTick />} />
            <YAxis tickLine={false} axisLine={false} width={40}
                   tick={{ fontSize: 11, fill: INK.axis }} />
            <Tooltip
              contentStyle={TOOLTIP}
              cursor={{ fill: '#faf9f7' }}
              itemSorter={(item) => TOP_DOWN.findIndex((s) => s.key === String(item.dataKey))}
            />
            {/* Recharts 3 no longer accepts a payload prop on Legend, and its generated one
                came out in an order matching neither the stack nor the tooltip. Rendering the
                key directly is both shorter and deterministic. */}
            <Legend verticalAlign="bottom" height={26} content={<StackLegend />} />

            <Bar dataKey="mapped" name="Mapped" stackId="a" fill={RAMP[3]}
                 {...chartMotion(reduced)}>
              {rows.map((r) => (
                <Cell key={r.org} fill={RAMP[3]} fillOpacity={orgOpacity(r.org, focus)}
                      cursor="pointer" onClick={() => toggle(r.org)}
                      onMouseEnter={() => hover(r.org)} />
              ))}
            </Bar>
            <Bar dataKey="pending" name="Still to review" stackId="a" fill={RAMP[0]}
                 {...chartMotion(reduced)}>
              {rows.map((r) => (
                <Cell key={r.org} fill={RAMP[0]} fillOpacity={orgOpacity(r.org, focus)}
                      cursor="pointer" onClick={() => toggle(r.org)}
                      onMouseEnter={() => hover(r.org)} />
              ))}
            </Bar>
            <Bar dataKey="dead" name="Dead codes" stackId="a" fill={STATUS.critical}
                 radius={[5, 5, 0, 0]} {...chartMotion(reduced)}>
              {rows.map((r) => (
                <Cell key={r.org} fill={STATUS.critical} fillOpacity={orgOpacity(r.org, focus)}
                      cursor="pointer" onClick={() => toggle(r.org)}
                      onMouseEnter={() => hover(r.org)} />
              ))}
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
