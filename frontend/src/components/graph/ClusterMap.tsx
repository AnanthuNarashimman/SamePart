import { useMemo, useState } from 'react'
import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'

// One canvas, not a grid of thumbnails.
//
// The previous version drew each cluster into its own small box, seven across, where a
// constellation is about ninety pixels wide and reads as a grey blob. Nothing about that
// says "national material master". Here every cluster lives in one space with room to
// breathe, placed on a golden-angle spiral so the field looks organic rather than tabulated,
// and sized by how many CPSE codes resolved into it.

const GOLDEN = Math.PI * (3 - Math.sqrt(5))

interface Placed {
  cluster: GraphCluster
  cx: number
  cy: number
  radius: number
}

function layout(clusters: GraphCluster[], w: number, h: number): Placed[] {
  const cxMid = w / 2
  const cyMid = h / 2
  // Spread across the shorter axis so nothing clips at the top or bottom.
  const spread = Math.min(w, h) * 0.46
  return clusters.map((cluster, i) => {
    const t = (i + 0.5) / clusters.length
    const r = spread * Math.sqrt(t)
    const angle = i * GOLDEN
    const size = cluster.members.length + cluster.alternatives.length
    return {
      cluster,
      cx: cxMid + Math.cos(angle) * r * (w / Math.min(w, h)) * 0.82,
      cy: cyMid + Math.sin(angle) * r,
      radius: 16 + size * 2.4,
    }
  })
}

export function ClusterMap({
  clusters,
  selected,
  onSelect,
}: {
  clusters: GraphCluster[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  const [hover, setHover] = useState<string | null>(null)
  const W = 1000
  const H = 560
  const placed = useMemo(() => layout(clusters, W, H), [clusters])
  const focus = hover ?? selected

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
         aria-label="Every national identity and the CPSE codes that resolved into it">
      {placed.map(({ cluster, cx, cy, radius }) => {
        const nodes = [...cluster.members, ...cluster.alternatives]
        const isFocus = focus === cluster.canonical_id
        // Everything not in focus recedes rather than disappears, so the field stays whole.
        const dim = focus && !isFocus ? 0.16 : 1

        return (
          <g
            key={cluster.canonical_id}
            opacity={dim}
            style={{ transition: 'opacity 180ms ease' }}
            onMouseEnter={() => setHover(cluster.canonical_id)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect(cluster.canonical_id)}
            className="cursor-pointer"
          >
            <title>
              {`${cluster.standardised_short ?? cluster.canonical_id} — ${cluster.members.length} codes across ${cluster.orgs.length} CPSEs`}
            </title>

            {nodes.map((m, i) => {
              const a = (i / nodes.length) * Math.PI * 2 - Math.PI / 2
              const x = cx + Math.cos(a) * radius
              const y = cy + Math.sin(a) * radius
              const alt = m.relation === 'alternative'
              return (
                <g key={`${m.record_id}-${i}`}>
                  <line
                    x1={cx} y1={cy} x2={x} y2={y}
                    stroke={alt ? '#d6d3d1' : '#d9d6d2'}
                    strokeWidth={isFocus ? 1.4 : 1}
                    strokeDasharray={alt ? '3 3' : undefined}
                  />
                  <circle
                    cx={x} cy={y} r={isFocus ? 6 : 4.5}
                    fill={alt ? '#ffffff' : orgColour(m.org_code)}
                    stroke={alt ? orgColour(m.org_code) : '#ffffff'}
                    strokeWidth={alt ? 1.6 : 1.2}
                    style={{ transition: 'r 180ms ease' }}
                  />
                </g>
              )
            })}

            {/* The minted identity, at the centre of everything that resolved into it. */}
            <circle cx={cx} cy={cy} r={isFocus ? 13 : 11} fill="#1c1917"
                    style={{ transition: 'r 180ms ease' }} />
            <text x={cx} y={cy + 3.6} textAnchor="middle" fontSize="10"
                  fontWeight="600" fill="#ffffff" pointerEvents="none">
              {cluster.members.length}
            </text>

            {/* A label only on the cluster in focus. Twenty-one labels at once is noise. */}
            {isFocus && cluster.standardised_short && (
              <text x={cx} y={cy + radius + 20} textAnchor="middle" fontSize="11"
                    fill="#57534e" pointerEvents="none">
                {cluster.standardised_short}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
