// Every identity cluster at once, from live data, with one opened up beside it.
//
// The previous version was five hardcoded nodes showing a single cluster, and every source
// node carried the caption "merged — all attributes agree". That states the answer and hides
// the problem. The problem is that four organisations describe the same bolt in ways nothing
// would reconcile, and that only becomes visible when you can read what they actually wrote.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ClusterDetail } from '../components/graph/ClusterDetail'
import { ClusterField } from '../components/graph/ClusterField'
import { QueryState } from '../components/shared/QueryState'
import { orgColour } from '../components/insights/tokens'

export function RelationshipGraph() {
  const graph = useGraph(21)
  const [picked, setPicked] = useState<string | null>(null)

  const clusters = graph.data?.clusters ?? []
  const selected = clusters.find((c) => c.canonical_id === picked) ?? clusters[0]
  const orgs = Array.from(new Set(clusters.flatMap((c) => c.orgs))).sort()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Relationship graph</h1>
        <p className="text-sm text-stone-400">
          {graph.data
            ? `${graph.data.total_clusters} national identities built from ${graph.data.total_records} CPSE material codes`
            : 'Identity clusters across the connected CPSEs'}
        </p>
      </header>

      {!graph.data ? (
        <div className="flex h-64 items-center justify-center rounded-2xl border border-stone-100 bg-white">
          <QueryState isLoading={graph.isLoading} isError={graph.isError} error={graph.error} />
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[1.15fr_1fr]">
          <section className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
            <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h2 className="text-sm font-semibold text-stone-900">Every cluster at once</h2>
              <ul className="flex flex-wrap items-center gap-3">
                {orgs.map((o) => (
                  <li key={o} className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: orgColour(o) }} />
                    <span className="font-mono text-[11px] text-stone-500">{o}</span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="mb-5 text-xs leading-relaxed text-stone-400">
              Each constellation is one national identity. The dark centre is the code we
              minted; every dot around it is a CPSE material code that resolved to it, coloured
              by which organisation it came from. A hollow dot is linked as a substitute rather
              than merged. Pick one to read what those codes actually said.
            </p>
            <ClusterField
              clusters={clusters}
              selected={selected?.canonical_id ?? null}
              onSelect={setPicked}
            />
            <p className="mt-4 border-t border-stone-100 pt-3 text-[11px] text-stone-400">
              Showing the {graph.data.shown} clusters spanning the most organisations, of{' '}
              {graph.data.total_clusters} in total.
            </p>
          </section>

          {selected && <ClusterDetail cluster={selected} />}
        </div>
      )}
    </div>
  )
}
