// Every identity cluster at once, from live data, with one opened up beside it.
//
// The previous version was five hardcoded nodes showing a single cluster, and every source
// node carried the caption "merged — all attributes agree". That states the answer and hides
// the problem. The problem is that four organisations describe the same bolt in ways nothing
// would reconcile, and that only becomes visible when you can read what they actually wrote.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ClusterDetail } from '../components/graph/ClusterDetail'
import { ClusterMap } from '../components/graph/ClusterMap'
import { QueryState } from '../components/shared/QueryState'
import { orgColour } from '../components/insights/tokens'

export function RelationshipGraph() {
  const graph = useGraph(28)
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
        <div className="flex flex-col gap-5">
          {/* The map gets the room. It is the only thing on the page that shows scale. */}
          <section className="rounded-2xl border border-stone-100 bg-white p-6 shadow-sm">
            <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h2 className="text-sm font-semibold text-stone-900">
                The national material master, so far
              </h2>
              <ul className="flex flex-wrap items-center gap-3">
                {orgs.map((o) => (
                  <li key={o} className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: orgColour(o) }} />
                    <span className="font-mono text-[11px] text-stone-500">{o}</span>
                  </li>
                ))}
                <li className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full border-2 border-stone-300 bg-white" />
                  <span className="font-mono text-[11px] text-stone-400">substitute</span>
                </li>
              </ul>
            </div>
            <p className="mb-2 max-w-3xl text-xs leading-relaxed text-stone-400">
              Every dark centre is a national code we minted. Every dot around it is one CPSE&apos;s
              own material code that resolved into it, coloured by the organisation it came from.
              Hover to isolate a cluster, click to read what those codes actually said.
            </p>
            <ClusterMap
              clusters={clusters}
              selected={selected?.canonical_id ?? null}
              onSelect={setPicked}
            />
            <p className="border-t border-stone-100 pt-3 text-[11px] text-stone-400">
              Showing the {graph.data.shown} identities spanning the most organisations, of{' '}
              {graph.data.total_clusters} built so far from {graph.data.total_records} CPSE codes.
            </p>
          </section>

          {selected && (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <ClusterDetail cluster={selected} />
              <div className="rounded-2xl border border-stone-100 bg-stone-50 p-6">
                <h3 className="mb-2 text-sm font-semibold text-stone-900">Why this is hard</h3>
                <p className="text-xs leading-relaxed text-stone-500">
                  Nothing in those descriptions matches. One writes <code className="rounded bg-white px-1">M20X40</code>,
                  another <code className="rounded bg-white px-1">M20 x 40mm</code>, a third
                  <code className="rounded bg-white px-1">DIA 20MM; LG 40MM</code>. A text
                  comparison finds nothing in common. Each CPSE has been buying the same bolt
                  under its own code for years, and neither system had any way to know.
                </p>
                <p className="mt-3 text-xs leading-relaxed text-stone-500">
                  The match is made on extracted attributes rather than on the words: diameter,
                  length, property class, standard. Every value carries the substring that
                  proved it, so a reviewer can check the working rather than trust a score.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
