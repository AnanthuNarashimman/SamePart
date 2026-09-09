// Static, curated node graph of one demo cluster — read-only, no new backend logic.
// Deprioritised per knowledge/08-ranked-additions.md ("pretty, says little a judge cares
// about"); kept minimal and built last, underneath the Dashboard as optional polish.

const NODES = [
  { id: 'SMP-000002', label: 'SMP-000002', x: 260, y: 160, kind: 'canonical' },
  { id: 'BPCL-000118', label: 'BPCL-000118', x: 80, y: 60, kind: 'source', org: 'BPCL' },
  { id: 'CPCL-000041', label: 'CPCL-000041', x: 80, y: 260, kind: 'source', org: 'CPCL' },
  { id: 'IOCL-000233', label: 'IOCL-000233', x: 440, y: 60, kind: 'alt', org: 'IOCL' },
  { id: 'NTPC-000015', label: 'NTPC-000015', x: 440, y: 260, kind: 'source', org: 'NTPC' },
]

const EDGES: { from: string; to: string; kind: 'merged' | 'alternative' }[] = [
  { from: 'BPCL-000118', to: 'SMP-000002', kind: 'merged' },
  { from: 'CPCL-000041', to: 'SMP-000002', kind: 'merged' },
  { from: 'NTPC-000015', to: 'SMP-000002', kind: 'merged' },
  { from: 'IOCL-000233', to: 'SMP-000002', kind: 'alternative' },
]

const nodeById = Object.fromEntries(NODES.map((n) => [n.id, n]))

export function RelationshipGraph() {
  return (
    <div className="flex-1 overflow-y-auto bg-stone-50 p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Relationship graph</h1>
        <p className="text-sm text-stone-400">
          One curated cluster — how four source records resolve to a single canonical material
        </p>
      </header>

      <div className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
        <svg viewBox="0 0 520 320" className="mx-auto w-full max-w-2xl">
          {EDGES.map((e) => {
            const a = nodeById[e.from]
            const b = nodeById[e.to]
            return (
              <line
                key={`${e.from}-${e.to}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={e.kind === 'merged' ? '#34d399' : '#fbbf24'}
                strokeWidth={2}
                strokeDasharray={e.kind === 'alternative' ? '6 4' : undefined}
              />
            )
          })}
          {NODES.map((n) => (
            <g key={n.id}>
              <circle
                cx={n.x}
                cy={n.y}
                r={n.kind === 'canonical' ? 30 : 22}
                fill={n.kind === 'canonical' ? '#f97316' : n.kind === 'alt' ? '#fef3c7' : '#ffffff'}
                stroke={n.kind === 'canonical' ? '#ea580c' : '#d6d3d1'}
                strokeWidth={2}
              />
              <text
                x={n.x}
                y={n.y + (n.kind === 'canonical' ? 44 : 36)}
                textAnchor="middle"
                className="fill-stone-600 text-[10px] font-medium"
              >
                {n.label}
              </text>
            </g>
          ))}
        </svg>

        <div className="mt-6 flex justify-center gap-6 text-xs text-stone-500">
          <span className="flex items-center gap-1.5"><span className="h-2 w-6 rounded bg-emerald-400" /> merged into canonical</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-6 rounded bg-amber-400" /> possible alternative</span>
          <span className="flex items-center gap-1.5"><span className="h-4 w-4 rounded-full bg-orange-500" /> canonical material</span>
        </div>
      </div>

      <p className="mt-4 text-xs text-stone-400">
        Curated demo cluster, not a live traversal of the full canonical graph — see
        knowledge/08-ranked-additions.md.
      </p>
    </div>
  )
}
