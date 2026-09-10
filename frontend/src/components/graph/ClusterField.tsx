import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'

// The field: every cluster at once, as a small constellation. One cluster on its own looks
// like a diagram of something obvious; a page of them is the harmonisation itself.
//
// No text at this level on purpose. The shape is the message — a hub with records pulled in
// from several organisations — and text at this size would only be noise. Detail is one
// click away.
export function ClusterField({
  clusters,
  selected,
  onSelect,
}: {
  clusters: GraphCluster[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-7">
      {clusters.map((c) => {
        const nodes = [...c.members, ...c.alternatives]
        const isOn = selected === c.canonical_id
        return (
          <button
            key={c.canonical_id}
            onClick={() => onSelect(c.canonical_id)}
            title={`${c.standardised_short ?? c.canonical_id} — ${c.members.length} records across ${c.orgs.length} CPSEs`}
            className={`group rounded-xl border p-1.5 transition ${
              isOn ? 'border-stone-300 bg-stone-50' : 'border-transparent hover:border-stone-200'
            }`}
          >
            <svg viewBox="0 0 100 100" className="w-full">
              {nodes.map((m, i) => {
                const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2
                const x = 50 + Math.cos(angle) * 34
                const y = 50 + Math.sin(angle) * 34
                const alt = m.relation === 'alternative'
                return (
                  <g key={`${m.record_id}-${i}`}>
                    <line
                      x1="50" y1="50" x2={x} y2={y}
                      stroke={alt ? '#d6d3d1' : '#c7c4c0'} strokeWidth="1"
                      strokeDasharray={alt ? '3 3' : undefined}
                      vectorEffect="non-scaling-stroke"
                    />
                    <circle
                      cx={x} cy={y} r="7"
                      fill={alt ? '#ffffff' : orgColour(m.org_code)}
                      stroke={orgColour(m.org_code)} strokeWidth="1.6"
                      vectorEffect="non-scaling-stroke"
                    />
                  </g>
                )
              })}
              {/* The canonical identity at the centre, filled dark so convergence reads. */}
              <circle cx="50" cy="50" r="10" fill="#1c1917" />
              <text x="50" y="53.5" textAnchor="middle" fontSize="9" fill="#ffffff"
                    fontWeight="600">{c.members.length}</text>
            </svg>
            <p className="mt-1 truncate font-mono text-[9px] text-stone-400">
              {c.orgs.length} CPSEs
            </p>
          </button>
        )
      })}
    </div>
  )
}
