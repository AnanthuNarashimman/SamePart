// Three questions, in the order a reader asks them, laid out as a workspace rather than a
// scroll.
//
//   Compression — 530 messy codes became 182 identities. One block, at the top, once.
//   Consensus   — which CPSEs agree on which identity. A matrix, because that is what
//                 agreement is.
//   Proof       — why these unrecognisably different descriptions are the same material.
//
// The proof used to sit a long way below the matrix, so clicking a row and seeing why it
// merged were separated by a scroll — which weakens the one relationship the page exists to
// show. It is now pinned beside the matrix, on a dark surface, so selecting a row and reading
// its evidence happen in the same glance.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ConsensusMatrix } from '../components/graph/ConsensusMatrix'
import { EvidenceInspector } from '../components/graph/EvidenceInspector'
import { ProofPanel } from '../components/graph/ProofPanel'
import { orgColour } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'
import { Card } from '@/components/ui/card'

/** Before and after, on one track. Four source masters stacked to their real proportions,
 *  then the same material as a much shorter bar. Both bars share a scale, so the gap between
 *  their lengths is the product, and it costs one row to say. */
function CompressionStrip({
  byOrg,
  orgs,
  identities,
  sourceCodes,
}: {
  byOrg: Record<string, number>
  orgs: string[]
  identities: number
  sourceCodes: number
}) {
  return (
    <div className="grid items-center gap-3 sm:grid-cols-[1fr_auto_1fr] sm:gap-4">
      <div className="min-w-0">
        <div className="flex h-8 w-full gap-[2px] overflow-hidden rounded-md">
          {orgs.map((o) => (
            <div
              key={o}
              className="flex items-center justify-center"
              style={{ width: `${((byOrg[o] ?? 0) / sourceCodes) * 100}%`, background: orgColour(o) }}
              title={`${o} · ${byOrg[o]} codes`}
            >
              <span className="font-mono text-[10px] font-semibold text-white">{byOrg[o]}</span>
            </div>
          ))}
        </div>
      </div>

      <span aria-hidden className="hidden shrink-0 text-lg text-stone-300 sm:block">→</span>

      <div className="min-w-0">
        <div className="h-8 w-full overflow-hidden rounded-md bg-stone-100">
          <div
            className="flex h-full items-center justify-end rounded-md bg-stone-900 pr-2"
            style={{ width: `${(identities / sourceCodes) * 100}%` }}
          >
            <span className="font-mono text-[10px] font-semibold text-white">
              {((identities / sourceCodes) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function RelationshipGraph() {
  const graph = useGraph(40)
  const [picked, setPicked] = useState<string | null>(null)
  const [hoverAttr, setHoverAttr] = useState<string | null>(null)
  const [pinnedAttr, setPinnedAttr] = useState<string | null>(null)
  const lit = pinnedAttr ?? hoverAttr

  const clusters = graph.data?.clusters ?? []
  const selected = clusters.find((c) => c.canonical_id === picked) ?? clusters[0]
  const stats = graph.data?.stats
  const orgs = Object.keys(stats?.by_org ?? {}).sort()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      {!graph.data || !stats ? (
        <Card className="flex h-64 items-center justify-center">
          <QueryState isLoading={graph.isLoading} isError={graph.isError} error={graph.error} loadingLabel="Drawing the registry" />
        </Card>
      ) : (
        <>
          {/* The hero is one block: the reduction, the bars that show it, and the three
              numbers that qualify it. Previously these were three separate bands of text and
              the compression never landed as a single fact. */}
          <section className="mb-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <p className="font-mono text-[10px] uppercase tracking-widest text-stone-400">
              relationship graph
            </p>

            <div className="mt-2 mb-5 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <span className="font-mono text-5xl font-semibold leading-none tracking-tight text-stone-900 sm:text-6xl">
                {stats.source_codes}
              </span>
              <span className="text-sm text-stone-500">source codes</span>
              <span aria-hidden className="text-3xl font-light text-stone-300">→</span>
              <span className="font-mono text-5xl font-semibold leading-none tracking-tight text-stone-900 sm:text-6xl">
                {stats.identities}
              </span>
              <span className="text-sm text-stone-500">national identities</span>
            </div>

            <CompressionStrip
              byOrg={stats.by_org}
              orgs={orgs}
              identities={stats.identities}
              sourceCodes={stats.source_codes}
            />

            <ul className="mt-5 flex flex-wrap gap-x-8 gap-y-2 border-t border-stone-100 pt-4">
              {[
                [stats.resolved.toString(), 'redundant codes resolved'],
                [`${(stats.consolidation * 100).toFixed(1)}%`, 'consolidation'],
                [orgs.length.toString(), 'CPSEs unified'],
              ].map(([v, k]) => (
                <li key={k} className="flex items-baseline gap-2">
                  <span className="font-mono text-xl font-semibold tabular-nums text-stone-900">{v}</span>
                  <span className="text-xs text-stone-500">{k}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Matrix and proof side by side. Selecting a row and reading why it merged should
              not be separated by a scroll. */}
          <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(380px,430px)]">
            <section className="min-w-0">
              <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-stone-900">Who agrees on what</h2>
                  <p className="text-xs text-stone-500">
                    One row per national identity, one column per CPSE. The bigger the dot, the
                    more codes that CPSE folded in.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {orgs.map((o) => (
                    <span key={o}
                          className="flex items-center gap-1.5 rounded-full border border-stone-200
                                     bg-white px-2 py-0.5 font-mono text-[11px] text-stone-600">
                      <span className="h-2 w-2 rounded-full" style={{ background: orgColour(o) }} />
                      {o} · {stats.by_org[o]}
                    </span>
                  ))}
                </div>
              </div>

              <ConsensusMatrix
                clusters={clusters}
                orgs={orgs}
                selected={selected?.canonical_id ?? null}
                onSelect={setPicked}
              />

              <p className="mt-2 text-xs text-stone-500">
                Showing {graph.data.shown} of {graph.data.total_clusters} identities. Click a row,
                or use the arrow keys, to prove it.
              </p>
            </section>

            {selected && (
              <aside className="min-w-0 xl:sticky xl:top-8">
                <ProofPanel
                  cluster={selected}
                  order={graph.data.attribute_order}
                  orgs={orgs}
                  lit={lit}
                  onLight={setHoverAttr}
                  pinned={pinnedAttr}
                  onPin={setPinnedAttr}
                />
              </aside>
            )}
          </div>

          {selected && (
            <section className="mt-5">
              {/* Folded away by default. It is the receipt, not the argument — the argument is
                  the panel above, and a reader who wants the raw text will open it. */}
              <details className="group rounded-2xl border border-stone-200 bg-white shadow-sm"
                       open>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-3.5">
                  <span>
                    <span className="text-sm font-semibold text-stone-900">
                      The words barely match. The attributes do.
                    </span>
                    <span className="mt-0.5 block text-xs text-stone-500">
                      {selected.members.length} codes from {selected.orgs.length} CPSEs. Hover any
                      value to light the exact words it was read from, in every row at once.
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-[11px] text-stone-400
                                   group-open:hidden">
                    show
                  </span>
                  <span className="hidden shrink-0 font-mono text-[11px] text-stone-400
                                   group-open:inline">
                    hide
                  </span>
                </summary>
                <div className="border-t border-stone-100">
                  <EvidenceInspector
                    cluster={selected}
                    order={graph.data.attribute_order}
                    lit={lit}
                    onLight={setHoverAttr}
                  />
                </div>
              </details>
            </section>
          )}
        </>
      )}
    </div>
  )
}
