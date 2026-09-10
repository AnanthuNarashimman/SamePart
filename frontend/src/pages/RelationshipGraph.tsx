// Three questions, three sections, in the order a reader asks them.
//
//   Compression — 520 messy codes became 178 identities. One strip, at the top, once.
//   Consensus   — which CPSEs agree on which identity. A matrix, because that is what
//                 agreement is.
//   Proof       — why these unrecognisably different descriptions are the same material.
//
// Earlier versions tried to make one ribbon diagram carry all three. It could not: a Sankey
// encodes flow between stages, and there are no stages here, only organisations and
// identities and the question of which agree. The ribbons were dramatic and after five
// seconds a reader still could not say which identities mattered, how many CPSEs agreed, or
// what had actually matched. Splitting the story into three views that each do one job beats
// one view that does none of them well.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ConsensusMatrix } from '../components/graph/ConsensusMatrix'
import { EvidenceFingerprint } from '../components/graph/EvidenceFingerprint'
import { EvidenceInspector } from '../components/graph/EvidenceInspector'
import { orgColour } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

/** Before and after, on one line. Four source masters stacked to their real proportions,
 *  then the same quantity of material as a much shorter bar of identities. The gap between
 *  the two bar lengths is the entire product, and it costs one row to say. */
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
    // Both tracks are the same width, so the second bar filling a third of its track is a
    // direct, honest picture of 178 out of 520. An earlier version gave the right-hand side a
    // narrower container and then scaled the bar back up to fill it, which drew a nearly-full
    // bar and said the opposite of what the numbers say.
    <div className="grid items-center gap-2.5 sm:grid-cols-[1fr_auto_1fr] sm:gap-5">
      <div className="min-w-0">
        <div className="mb-1.5 flex items-baseline justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            source codes
          </span>
          <span className="font-mono text-[11px] tabular-nums text-stone-500">{sourceCodes}</span>
        </div>
        <div className="flex h-7 w-full gap-[2px] overflow-hidden rounded-md">
          {orgs.map((o) => (
            <div
              key={o}
              className="flex items-center justify-center"
              style={{ width: `${((byOrg[o] ?? 0) / sourceCodes) * 100}%`, background: orgColour(o) }}
              title={`${o} · ${byOrg[o]} codes`}
            >
              <span className="font-mono text-[10px] font-medium text-white/90">{byOrg[o]}</span>
            </div>
          ))}
        </div>
      </div>

      <span aria-hidden className="hidden shrink-0 text-lg text-stone-300 sm:block">→</span>

      <div className="min-w-0">
        <div className="mb-1.5 flex items-baseline justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            national identities
          </span>
          <span className="font-mono text-[11px] tabular-nums text-stone-500">{identities}</span>
        </div>
        {/* Same track width as the left bar, so the shortening is the message. */}
        <div className="h-7 w-full overflow-hidden rounded-md bg-stone-100">
          <div
            className="flex h-full items-center justify-end rounded-md bg-stone-900 pr-2"
            style={{ width: `${(identities / sourceCodes) * 100}%` }}
          >
            <span className="font-mono text-[10px] font-medium text-white/90">
              {((identities / sourceCodes) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function RelationshipGraph() {
  // A matrix reads more rows comfortably than a ribbon diagram ever could.
  const graph = useGraph(40)
  const [picked, setPicked] = useState<string | null>(null)
  const [lit, setLit] = useState<string | null>(null)

  const clusters = graph.data?.clusters ?? []
  const selected = clusters.find((c) => c.canonical_id === picked) ?? clusters[0]
  const stats = graph.data?.stats
  const orgs = Object.keys(stats?.by_org ?? {}).sort()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      {!graph.data || !stats ? (
        <Card className="flex h-64 items-center justify-center">
          <QueryState isLoading={graph.isLoading} isError={graph.isError} error={graph.error} />
        </Card>
      ) : (
        <>
          <header className="mb-5">
            <p className="mb-1 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              relationship graph
            </p>
            <h1 className="font-mono text-4xl leading-none tracking-tight text-foreground sm:text-5xl">
              {stats.source_codes} codes <span className="text-muted-foreground">→</span>{' '}
              {stats.identities} identities
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {stats.resolved} redundant codes resolved across {orgs.length} CPSEs ·{' '}
              {(stats.consolidation * 100).toFixed(1)}% consolidation
            </p>
          </header>

          <Card className="mb-6">
            <CardContent className="py-4">
              <CompressionStrip
                byOrg={stats.by_org}
                orgs={orgs}
                identities={stats.identities}
                sourceCodes={stats.source_codes}
              />
            </CardContent>
          </Card>

          <section className="mb-6">
            <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Who agrees on what</h2>
                <p className="text-xs text-muted-foreground">
                  One row per national identity, one column per CPSE. A filled dot means that
                  CPSE contributed source codes to this identity; the bigger the dot, the more
                  it contributed.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {orgs.map((o) => (
                  <Badge key={o} variant="outline" className="gap-1.5 font-mono text-[11px]">
                    <span className="h-2 w-2 rounded-full" style={{ background: orgColour(o) }} />
                    {o} · {stats.by_org[o]}
                  </Badge>
                ))}
              </div>
            </div>

            <ConsensusMatrix
              clusters={clusters}
              orgs={orgs}
              selected={selected?.canonical_id ?? null}
              onSelect={setPicked}
            />

            <p className="mt-2 text-xs text-muted-foreground">
              Showing {graph.data.shown} identities of {graph.data.total_clusters}. Click a row to
              see why its codes were merged.
            </p>
          </section>

          {selected && (
            <section className="flex flex-col gap-5">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Why these are one material</h2>
                <p className="text-xs text-muted-foreground">
                  The descriptions below share almost no words. The extracted attributes are
                  identical, and every one of them is traceable to the text it came from.
                </p>
              </div>

              <Card>
                <CardContent className="py-5">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    canonical identity
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
                    {(selected.standardised_short ?? '').split(';')[0]}
                  </h2>
                  <p className="mt-0.5 font-mono text-lg text-foreground">
                    {(selected.standardised_short ?? '').split(';').slice(1).join(' · ').trim()}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <Badge variant="outline" className="font-mono text-[11px]">
                      {selected.national_code}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {selected.orgs.length} CPSEs · {selected.members.length} source codes
                      {selected.alternatives.length > 0 &&
                        ` · ${selected.alternatives.length} substitute${
                          selected.alternatives.length > 1 ? 's' : ''
                        } held separate`}
                    </span>
                  </div>
                  <Separator className="my-4" />
                  <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    independent evidence, by attribute
                  </p>
                  <EvidenceFingerprint
                    cluster={selected}
                    order={graph.data.attribute_order}
                    orgs={orgs}
                    lit={lit}
                    onLight={setLit}
                  />
                  <p className="mt-3 text-xs text-muted-foreground">
                    A filled dot means that CPSE&apos;s own description carried this fact. Hollow
                    means it stated something different. Hover any attribute to light the exact
                    words below.
                  </p>
                </CardContent>
              </Card>

              <EvidenceInspector
                cluster={selected}
                order={graph.data.attribute_order}
                lit={lit}
                onLight={setLit}
              />
            </section>
          )}
        </>
      )}
    </div>
  )
}
