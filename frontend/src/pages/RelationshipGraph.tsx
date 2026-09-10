// 437 messy CPSE codes compressing into 159 trusted identities, with the evidence.
//
// Three earlier versions drew connectivity — which dot joined which dot — on white, with
// hairlines and a KPI card. None of them felt like compression. This one puts the numbers
// themselves at the top as the hero, gives the convergence a dark analytical surface where
// ribbon width is the number of codes collapsed, and lets one hover light the same fact
// across the fingerprint and every raw description at once.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ConvergenceSankey } from '../components/graph/ConvergenceSankey'
import { EvidenceFingerprint } from '../components/graph/EvidenceFingerprint'
import { EvidenceInspector } from '../components/graph/EvidenceInspector'
import { orgColour } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

export function RelationshipGraph() {
  const graph = useGraph(16)
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
          {/* The numbers are the hero. No card, no border — a box around this would only
              make it smaller. */}
          <header className="mb-7">
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

          <section className="mb-6">
            <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Material convergence</h2>
                <p className="text-xs text-muted-foreground">
                  Ribbon width is how many codes collapsed along it. A dashed tie is a
                  substitute, which never merges into the identity.
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
            <ConvergenceSankey
              clusters={clusters}
              orgs={orgs}
              perOrgTotal={stats.by_org}
              selected={selected?.canonical_id ?? null}
              onSelect={setPicked}
            />
            <p className="mt-2 text-xs text-muted-foreground">
              Showing {graph.data.shown} identities of {graph.data.total_clusters}, ranked by how
              many organisations they span.
            </p>
          </section>

          {selected && (
            <div className="flex flex-col gap-5">
              {/* The selected identity, at a size that says it is the destination. */}
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
            </div>
          )}
        </>
      )}
    </div>
  )
}
