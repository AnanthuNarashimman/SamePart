// Static, curated node graph of one demo cluster — read-only, no new backend logic.
// Deprioritised per knowledge/08-ranked-additions.md ("pretty, says little a judge cares
// about"); kept as optional polish underneath the Dashboard. Rendered with @xyflow/react
// (React Flow) instead of a hand-rolled SVG so it actually pans/zooms and reads as a real
// graph — pan, zoom, minimap, fit-view — even though the underlying data stays curated.
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useMemo } from 'react'

type NodeKind = 'canonical' | 'source' | 'alt'

interface DemoNodeData extends Record<string, unknown> {
  code: string
  org: string
  kind: NodeKind
  detail: string
}

const RAW_NODES: { id: string; x: number; y: number; kind: NodeKind; org: string; detail: string }[] = [
  { id: 'SMP-000002', x: 380, y: 200, kind: 'canonical', org: 'canonical', detail: 'BOLT, HEX HEAD; M10X120; A2-70; DIN931' },
  { id: 'BPCL-000118', x: 60, y: 40, kind: 'source', org: 'BPCL', detail: 'Merged — all attributes agree' },
  { id: 'CPCL-000041', x: 60, y: 200, kind: 'source', org: 'CPCL', detail: 'Merged — all attributes agree' },
  { id: 'NTPC-000015', x: 60, y: 360, kind: 'source', org: 'NTPC', detail: 'Merged — all attributes agree' },
  { id: 'IOCL-000233', x: 700, y: 200, kind: 'alt', org: 'IOCL', detail: 'Possible alternative — grade differs (A4-70)' },
]

const RAW_EDGES: { from: string; to: string; kind: 'merged' | 'alternative' }[] = [
  { from: 'BPCL-000118', to: 'SMP-000002', kind: 'merged' },
  { from: 'CPCL-000041', to: 'SMP-000002', kind: 'merged' },
  { from: 'NTPC-000015', to: 'SMP-000002', kind: 'merged' },
  { from: 'IOCL-000233', to: 'SMP-000002', kind: 'alternative' },
]

const KIND_STYLE: Record<NodeKind, { ring: string; bg: string; text: string; dot: string }> = {
  canonical: { ring: 'border-primary-500', bg: 'bg-primary-500', text: 'text-white', dot: 'bg-white' },
  source: { ring: 'border-brand-300', bg: 'bg-white', text: 'text-stone-800', dot: 'bg-brand-500' },
  alt: { ring: 'border-khaki-300', bg: 'bg-khaki-50', text: 'text-stone-800', dot: 'bg-khaki-500' },
}

function DemoNode({ data }: NodeProps<Node<DemoNodeData>>) {
  const style = KIND_STYLE[data.kind]
  const isCanonical = data.kind === 'canonical'

  return (
    <div
      className={`flex flex-col items-center gap-1 rounded-2xl border-2 px-4 py-3 shadow-sm ${style.ring} ${style.bg} ${style.text}`}
      style={{ minWidth: isCanonical ? 200 : 160 }}
    >
      <Handle type="target" position={Position.Left} className="!bg-stone-300" />
      <Handle type="source" position={Position.Right} className="!bg-stone-300" />
      <div className="flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
        <span className="font-mono text-xs font-semibold">{data.code}</span>
      </div>
      {!isCanonical && <span className="text-[10px] uppercase tracking-wide opacity-60">{data.org}</span>}
      <p className={`max-w-[13rem] text-center text-[10px] leading-snug ${isCanonical ? 'text-white/80' : 'text-stone-500'}`}>
        {data.detail}
      </p>
    </div>
  )
}

const nodeTypes = { demo: DemoNode }

interface DemoEdgeData extends Record<string, unknown> {
  kind: 'merged' | 'alternative'
}

function DemoEdge({ sourceX, sourceY, targetX, targetY, data }: EdgeProps<Edge<DemoEdgeData>>) {
  const merged = data?.kind !== 'alternative'
  const midX = (sourceX + targetX) / 2
  const path = `M ${sourceX},${sourceY} C ${midX},${sourceY} ${midX},${targetY} ${targetX},${targetY}`
  return (
    <path
      d={path}
      fill="none"
      stroke={merged ? '#34d399' : '#f59e0b'}
      strokeWidth={2.5}
      strokeDasharray={merged ? undefined : '7 5'}
      markerEnd="url(#demo-arrow)"
    />
  )
}

const edgeTypes = { demo: DemoEdge }

// The graph on its own, so it can sit inside the Insights page as the closing visual as well
// as standing alone. Same nodes, same edges, same look.
export function ClusterGraph() {
  const nodes = useMemo<Node<DemoNodeData>[]>(
    () =>
      RAW_NODES.map((n) => ({
        id: n.id,
        type: 'demo',
        position: { x: n.x, y: n.y },
        data: { code: n.id, org: n.org, kind: n.kind, detail: n.detail },
        draggable: true,
      })),
    [],
  )

  const edges = useMemo<Edge<DemoEdgeData>[]>(
    () =>
      RAW_EDGES.map((e) => ({
        id: `${e.from}-${e.to}`,
        source: e.from,
        target: e.to,
        type: 'demo',
        data: { kind: e.kind },
      })),
    [],
  )

  return (
    <div className="relative h-full w-full overflow-hidden bg-white">
        <svg width="0" height="0">
          <defs>
            <marker id="demo-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#a8a29e" />
            </marker>
          </defs>
        </svg>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          proOptions={{ hideAttribution: true }}
          nodesConnectable={false}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e7e5e4" />
          <Controls showInteractive={false} position="top-right" className="!rounded-xl !border !border-stone-100 !shadow-sm" />
        </ReactFlow>

        <div className="absolute bottom-4 left-4 flex flex-wrap gap-4 rounded-xl bg-white/90 px-4 py-2 text-xs text-stone-500 shadow-sm backdrop-blur">
          <span className="flex items-center gap-1.5"><span className="h-2 w-6 rounded bg-brand-400" /> merged into canonical</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-6 rounded border border-dashed border-khaki-500" /> possible alternative</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-primary-500" /> canonical material</span>
        </div>
    </div>
  )
}


// The standalone page, unchanged in what it shows.
export function RelationshipGraph() {
  return (
    <div className="flex flex-1 flex-col overflow-hidden app-canvas p-8">
      <header className="mb-6 shrink-0">
        <h1 className="text-xl font-semibold text-stone-900">Relationship graph</h1>
        <p className="text-sm text-stone-400">
          One curated cluster — how four source records resolve to a single canonical material.
          Drag nodes, scroll to zoom, or use the controls in the corner.
        </p>
      </header>

      <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-stone-100 shadow-sm">
        <ClusterGraph />
      </div>

      <p className="mt-4 shrink-0 text-xs text-stone-400">
        Curated demo cluster, not a live traversal of the full canonical graph — see
        knowledge/08-ranked-additions.md.
      </p>
    </div>
  )
}
