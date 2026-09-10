import { useMemo, useState } from 'react'
import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'

// Source lanes on the left, national identities on the right, flows between them.
//
// This replaces a field of constellations. That view drew every identity as the same star,
// so position on the canvas carried no information and the picture said only "there are
// clusters". The data is not a network — it is a convergence — and this draws the thing that
// actually happened: four incompatible catalogues collapsing into one master.
//
// Solid means same identity. Dashed means an approved substitute candidate, which is a
// different claim entirely and gets a different line rather than a subtler dot.

const LANE_X = 118
const LANE_GAP = 74
const NODE_X = 640
const ROW_H = 34
const TOP = 42

export function ConvergenceMap({
  clusters,
  orgs,
  selected,
  onSelect,
}: {
  clusters: GraphCluster[]
  orgs: string[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  const [hover, setHover] = useState<string | null>(null)
  const focus = hover ?? selected
  const laneX = useMemo(
    () => Object.fromEntries(orgs.map((o, i) => [o, LANE_X + i * LANE_GAP])),
    [orgs],
  )
  const height = TOP + clusters.length * ROW_H + 30

  return (
    <svg viewBox={`0 0 860 ${height}`} className="w-full" role="img"
         aria-label="CPSE material codes converging into national identities">
      {/* The lanes. Each company's codes start here. */}
      {orgs.map((o) => (
        <g key={o}>
          <text x={laneX[o]} y={22} textAnchor="middle" fontSize="11" fontWeight="600"
                fill={orgColour(o)} fontFamily="ui-monospace, monospace">{o}</text>
          <line x1={laneX[o]} y1={32} x2={laneX[o]} y2={height - 18}
                stroke="#e7e5e4" strokeWidth="1" />
        </g>
      ))}
      <text x={NODE_X + 14} y={22} fontSize="11" fontWeight="600" fill="#78716c"
            fontFamily="ui-monospace, monospace">NATIONAL IDENTITY</text>

      {clusters.map((cluster, row) => {
        const y = TOP + row * ROW_H + ROW_H / 2
        const isFocus = focus === cluster.canonical_id
        const dim = focus && !isFocus ? 0.12 : 1
        const nodes = [...cluster.members, ...cluster.alternatives]

        return (
          <g
            key={cluster.canonical_id}
            opacity={dim}
            style={{ transition: 'opacity 160ms ease' }}
            onMouseEnter={() => setHover(cluster.canonical_id)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect(cluster.canonical_id)}
            className="cursor-pointer"
          >
            <title>
              {`${cluster.standardised_short ?? cluster.canonical_id} — ${cluster.members.length} codes from ${cluster.orgs.length} CPSEs`}
            </title>
            {/* A generous hit target: the row, not the 4px line. */}
            <rect x="0" y={y - ROW_H / 2} width="860" height={ROW_H} fill="transparent" />

            {nodes.map((m, i) => {
              const sx = laneX[m.org_code] ?? LANE_X
              // Stack duplicates from one company so their flows stay separable.
              const sy = y + ((i % 3) - 1) * 5
              const alt = m.relation === 'alternative'
              const mid = sx + (NODE_X - sx) * 0.55
              return (
                <g key={`${m.record_id}-${i}`}>
                  <path
                    d={`M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${y}, ${NODE_X - 12} ${y}`}
                    fill="none"
                    stroke={alt ? '#a8a29e' : orgColour(m.org_code)}
                    strokeWidth={isFocus ? 1.7 : 1.1}
                    strokeOpacity={alt ? 0.85 : 0.55}
                    strokeDasharray={alt ? '4 3' : undefined}
                    style={{ transition: 'stroke-width 160ms ease' }}
                  />
                  <circle cx={sx} cy={sy} r={isFocus ? 4 : 3}
                          fill={alt ? '#ffffff' : orgColour(m.org_code)}
                          stroke={orgColour(m.org_code)} strokeWidth="1.2" />
                </g>
              )
            })}

            <circle cx={NODE_X} cy={y} r={isFocus ? 7 : 5.5} fill="#1c1917"
                    style={{ transition: 'r 160ms ease' }} />
            <text x={NODE_X + 14} y={y + 3.5} fontSize="10.5"
                  fill={isFocus ? '#1c1917' : '#78716c'}
                  fontFamily="ui-monospace, monospace">
              {(cluster.standardised_short ?? cluster.canonical_id).replace('BOLT, HEX HEAD; ', '')}
            </text>
            <text x="852" y={y + 3.5} textAnchor="end" fontSize="10" fill="#a8a29e"
                  fontFamily="ui-monospace, monospace">
              {cluster.members.length}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
