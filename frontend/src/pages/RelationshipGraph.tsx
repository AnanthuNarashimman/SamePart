// 437 messy CPSE codes becoming 159 trusted national identities, with the evidence for every
// convergence.
//
// The page is built around that sentence. The result states it, the map draws it, and the
// inspector proves it for whichever identity you pick. An earlier version drew every identity
// as a constellation, which looked like a network but was not one: the data is a convergence,
// every cluster was the same star shape, and position on the canvas meant nothing.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ConvergenceMap } from '../components/graph/ConvergenceMap'
import { EvidenceInspector } from '../components/graph/EvidenceInspector'
import { orgColour } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

export function RelationshipGraph() {
  const graph = useGraph(18)
  const [picked, setPicked] = useState<string | null>(null)

  const clusters = graph.data?.clusters ?? []
  const selected = clusters.find((c) => c.canonical_id === picked) ?? clusters[0]
  const orgs = Object.keys(graph.data?.stats?.by_org ?? {}).sort()
  const stats = graph.data?.stats

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-5">
        <h1 className="text-xl font-semibold text-foreground">Relationship graph</h1>
        <p className="text-sm text-muted-foreground">
          Where every CPSE material code ended up, and what proved it
        </p>
      </header>

      {!graph.data || !stats ? (
        <Card className="flex h-64 items-center justify-center">
          <QueryState isLoading={graph.isLoading} isError={graph.isError} error={graph.error} />
        </Card>
      ) : (
        <div className="flex flex-col gap-5">
          {/* The result, first. A visualisation without a stated purpose is decoration. */}
          <Card>
            <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-4 py-5">
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-4xl leading-none text-foreground">
                  {stats.source_codes}
                </span>
                <span className="text-sm text-muted-foreground">material codes</span>
                <span className="px-1 text-2xl text-muted-foreground">→</span>
                <span className="font-mono text-4xl leading-none text-foreground">
                  {stats.identities}
                </span>
                <span className="text-sm text-muted-foreground">national identities</span>
              </div>
              <Separator orientation="vertical" className="hidden h-10 sm:block" />
              <div>
                <p className="font-mono text-lg leading-none text-foreground">
                  {stats.resolved} <span className="text-sm text-muted-foreground">redundant codes resolved</span>
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {(stats.consolidation * 100).toFixed(1)}% consolidation across{' '}
                  {orgs.length} CPSEs
                </p>
              </div>
              {/* A bar the width of the page: how much of the master was redundant. */}
              <div className="min-w-[220px] flex-1">
                <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
                  <div className="bg-primary" style={{ width: `${stats.consolidation * 100}%` }} />
                </div>
                <div className="mt-1 flex justify-between font-mono text-[10px] text-muted-foreground">
                  <span>redundant</span>
                  <span>distinct materials</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Material convergence</CardTitle>
              <CardDescription className="max-w-3xl">
                Each code begins in its own company&apos;s lane and flows to the national identity
                it resolved into. A solid line means the same material. A dashed line means an
                approved substitute, which is a different claim. Click a row to see the proof.
              </CardDescription>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {orgs.map((o) => (
                  <Badge key={o} variant="outline" className="gap-1.5 font-mono text-[11px]">
                    <span className="h-2 w-2 rounded-full" style={{ background: orgColour(o) }} />
                    {o} · {stats.by_org[o]}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <ConvergenceMap
                clusters={clusters}
                orgs={orgs}
                selected={selected?.canonical_id ?? null}
                onSelect={setPicked}
              />
              <Separator className="my-3" />
              <p className="text-xs text-muted-foreground">
                Showing {graph.data.shown} identities, ranked by how many organisations they span,
                of {graph.data.total_clusters}.
              </p>
            </CardContent>
          </Card>

          {selected && (
            <EvidenceInspector cluster={selected} order={graph.data.attribute_order} />
          )}
        </div>
      )}
    </div>
  )
}
