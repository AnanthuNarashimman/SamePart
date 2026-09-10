import { useEffect, useMemo, useRef, useState } from 'react'
import type { GraphCluster } from '../../api/types'
import { orgColourDark } from '../insights/tokens'

// Thick ribbons on a dark analytical surface, not hairlines on white.
//
// The previous version drew connectivity: which dot joined which dot. This draws COMPRESSION.
// A ribbon's width is how many source codes collapsed along it, so the picture is many wide
// flows on the left narrowing into a shorter column of identities on the right, which is the
// product in one image.
//
// Solid ribbon means same material. A substitute never flows into an identity block at all;
// it hangs off to the side on a dashed tie, because "these are the same thing" and "these are
// interchangeable under conditions" are different claims and should not share a shape.

// The chart is drawn at true pixel size rather than scaled to fit.
//
// It used to carry a fixed viewBox of 0 0 1000 715 on a full-width SVG, which means the
// browser scales it to preserve that 1.4:1 aspect: on an 1800px column the chart rendered
// 1,287px tall and the page had to scroll to see the bottom of it. It also meant every label
// grew with the window, so type was never the size it was set at. Measuring the container and
// mapping the viewBox 1:1 fixes both — the chart is exactly H tall on every screen, and 11px
// text is 11px.
const HEIGHT = 460
const LEFT_X = 104
const BLOCK_W = 13
const PAD = 20
// Room on the right for the identity label and the substitute ties that hang off it.
const LABEL_COL = 360

export function ConvergenceSankey({
  clusters,
  orgs,
  perOrgTotal,
  selected,
  onSelect,
}: {
  clusters: GraphCluster[]
  orgs: string[]
  perOrgTotal: Record<string, number>
  selected: string | null
  onSelect: (id: string) => void
}) {
  const [hover, setHover] = useState<string | null>(null)
  const focus = hover ?? selected

  const wrap = useRef<HTMLDivElement>(null)
  const [W, setW] = useState(1000)
  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) =>
      setW(Math.max(720, Math.round(entry.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const RIGHT_X = Math.max(320, W - LABEL_COL)

  const model = useMemo(() => {
    // Order identities by the average lane of whatever feeds them — the barycentre heuristic
    // every Sankey uses. Without it, sixteen destinations pulling from four lanes in an
    // arbitrary order produces a tangle; with it the ribbons run broadly parallel and the
    // picture reads as flow rather than as noise. This is the single biggest legibility win
    // available, and it costs one sort.
    const laneOf = Object.fromEntries(orgs.map((o, i) => [o, i]))
    const shown = [...clusters].sort((a, b) => {
      const bary = (c: GraphCluster) =>
        c.members.reduce((sum, m) => sum + (laneOf[m.org_code] ?? 0), 0) /
        Math.max(c.members.length, 1)
      return bary(a) - bary(b) || b.members.length - a.members.length
    })
    const totalRight = shown.reduce((a, c) => a + c.members.length, 0)
    // Height is now fixed, so the per-code unit is whatever divides into it rather than the
    // other way round. Every ribbon still scales with the codes it carries; the whole diagram
    // just fits on screen.
    const H = HEIGHT
    const rowGap = 7
    const unit = (H - PAD * 2 - shown.length * rowGap) / Math.max(totalRight, 1)

    let ry = PAD
    const right = shown.map((c) => {
      const h = Math.max(c.members.length * unit, 10)
      const block = { cluster: c, y: ry, h }
      ry += h + rowGap
      return block
    })

    // Left column: one block per CPSE, height by how many of the shown codes it contributed.
    const contrib: Record<string, number> = {}
    for (const c of shown) for (const m of c.members) contrib[m.org_code] = (contrib[m.org_code] ?? 0) + 1
    const totalLeft = Object.values(contrib).reduce((a, b) => a + b, 0)
    const laneGap = 22
    const lunit = (H - PAD * 2 - (orgs.length - 1) * laneGap) / Math.max(totalLeft, 1)

    let ly = PAD
    const left: Record<string, { y: number; h: number; cursor: number }> = {}
    for (const o of orgs) {
      const h = Math.max((contrib[o] ?? 0) * lunit, 8)
      left[o] = { y: ly, h, cursor: ly }
      ly += h + laneGap
    }

    // Ribbons, walking each identity in order so both ends stay untangled.
    const ribbons: { org: string; cluster: GraphCluster; y0: number; y1: number; t: number }[] = []
    for (const block of right) {
      const byOrg: Record<string, number> = {}
      for (const m of block.cluster.members) byOrg[m.org_code] = (byOrg[m.org_code] ?? 0) + 1
      let cursor = block.y
      for (const o of orgs) {
        const n = byOrg[o]
        if (!n) continue
        const t = n * unit
        ribbons.push({ org: o, cluster: block.cluster, y0: left[o].cursor + t / 2, y1: cursor + t / 2, t })
        left[o].cursor += t
        cursor += t
      }
    }
    return { H, right, left, ribbons, contrib }
  }, [clusters, orgs, RIGHT_X])

  return (
    <div ref={wrap} className="w-full">
    <svg viewBox={`0 0 ${W} ${model.H}`} width="100%" height={model.H} role="img"
         aria-label="CPSE material codes compressing into national identities">
      <rect x="0" y="0" width={W} height={model.H} fill="#161615" rx="14" />

      {/* Source blocks. */}
      {orgs.map((o) => {
        const b = model.left[o]
        const c = orgColourDark(o)
        return (
          <g key={o}>
            <rect x={LEFT_X} y={b.y} width={BLOCK_W} height={b.h} rx="6" fill={c} />
            {/* One line, centred on the block. Two stacked lines per lane was four extra
                pieces of text competing with the flows. */}
            <text x={LEFT_X - 14} y={b.y + b.h / 2 - 2} textAnchor="end" fontSize="13"
                  fontWeight="600" fill={c} fontFamily="ui-monospace, monospace">{o}</text>
            <text x={LEFT_X - 14} y={b.y + b.h / 2 + 12} textAnchor="end" fontSize="10"
                  fill="#57534e" fontFamily="ui-monospace, monospace">
              {perOrgTotal[o] ?? model.contrib[o]}
            </text>
          </g>
        )
      })}

      {model.ribbons.map((r, i) => {
        const isFocus = focus === r.cluster.canonical_id
        // Control points pulled apart rather than both at the midpoint. A symmetric S turns
        // the whole span into curve, so with forty ribbons the middle becomes a mesh. Pushing
        // the handles toward the ends gives each ribbon a long straight run through the
        // centre, and forty near-parallel lines read as flow where forty crossing curves read
        // as noise. Reordering the nodes barely helped here — nearly every identity draws
        // from all four lanes, so their barycentres are all alike — but this does.
        const span = RIGHT_X - (LEFT_X + BLOCK_W)
        const c1 = LEFT_X + BLOCK_W + span * 0.18
        const c2 = RIGHT_X - span * 0.18
        return (
          <path
            key={i}
            d={`M ${LEFT_X + BLOCK_W} ${r.y0} C ${c1} ${r.y0}, ${c2} ${r.y1}, ${RIGHT_X} ${r.y1}`}
            fill="none"
            stroke={orgColourDark(r.org)}
            strokeWidth={Math.max(r.t, 3)}
            // Butt, not round. A round cap extends half the stroke width past each endpoint,
            // so the widest ribbons — the ones carrying the most codes — overshot both the
            // source block and the identity block by twenty pixels and appeared to leak out
            // of the diagram. The thicker the ribbon, the worse it looked.
            strokeLinecap="butt"
            strokeOpacity={focus ? (isFocus ? 0.95 : 0.05) : 0.3}
            style={{ transition: 'stroke-opacity 160ms ease' }}
          />
        )
      })}

      {/* Identity blocks. High contrast, because this is the destination. */}
      {model.right.map(({ cluster, y, h }) => {
        const isFocus = focus === cluster.canonical_id
        const dim = focus && !isFocus ? 0.18 : 1
        const short = (cluster.standardised_short ?? cluster.canonical_id)
          .replace('BOLT, HEX HEAD; ', '')
        return (
          <g key={cluster.canonical_id} opacity={dim}
             style={{ transition: 'opacity 160ms ease' }}
             onMouseEnter={() => setHover(cluster.canonical_id)}
             onMouseLeave={() => setHover(null)}
             onClick={() => onSelect(cluster.canonical_id)}
             className="cursor-pointer">
            <title>{`${short} — ${cluster.members.length} codes from ${cluster.orgs.length} CPSEs`}</title>
            <rect x={RIGHT_X} y={y} width={BLOCK_W} height={h} rx="6"
                  fill={isFocus ? '#fafaf9' : '#8c8781'} />
            {/* The count sits inside the block, so the label column stays a single clean
                line of text instead of two competing ones. */}
            <text x={RIGHT_X + 24} y={y + h / 2 + 4} fontSize="11.5"
                  fill={isFocus ? '#fafaf9' : '#a8a29e'} fontFamily="ui-monospace, monospace">
              <tspan fill={isFocus ? '#fafaf9' : '#57534e'}>{cluster.members.length}×</tspan>
              <tspan dx="7">{short}</tspan>
            </text>

            {/* Substitutes hang off the block on a dashed tie. They never flow into it. */}
            {isFocus && cluster.alternatives.map((a, k) => (
              <g key={a.record_id}>
                <path
                  d={`M ${RIGHT_X + BLOCK_W} ${y + h / 2} C ${RIGHT_X + 60} ${y + h / 2},
                      ${RIGHT_X + 60} ${y + h + 26 + k * 16}, ${RIGHT_X + 96} ${y + h + 26 + k * 16}`}
                  fill="none" stroke="#78716c" strokeWidth="1.6" strokeDasharray="5 4"
                />
                <text x={RIGHT_X + 104} y={y + h + 30 + k * 16} fontSize="10" fill="#a8a29e"
                      fontFamily="ui-monospace, monospace">
                  substitute · {a.org_code}
                </text>
              </g>
            ))}
          </g>
        )
      })}
    </svg>
    </div>
  )
}
