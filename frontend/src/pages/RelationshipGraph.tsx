// Every national identity and the CPSE codes that resolved into it, on one canvas.
//
// Built on shadcn primitives rather than hand-rolled divs: Card supplies the surface and its
// header rhythm, Badge the counts, Separator the rules. Those carry the polish so the page's
// own code can be about the graph.
import { useState } from 'react'
import { useGraph } from '../api/analytics'
import { ClusterDetail } from '../components/graph/ClusterDetail'
import { ClusterMap } from '../components/graph/ClusterMap'
import { orgColour } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'
import { Badge } from '@/components/ui/badge'
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

export function RelationshipGraph() {
  const graph = useGraph(28)
  const [picked, setPicked] = useState<string | null>(null)

  const clusters = graph.data?.clusters ?? []
  const selected = clusters.find((c) => c.canonical_id === picked) ?? clusters[0]
  const orgs = Array.from(new Set(clusters.flatMap((c) => c.orgs))).sort()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Relationship graph</h1>
        <p className="text-sm text-muted-foreground">
          {graph.data
            ? `${graph.data.total_clusters} national identities, built from ${graph.data.total_records} CPSE material codes`
            : 'Identity clusters across the connected CPSEs'}
        </p>
      </header>

      {!graph.data ? (
        <Card className="flex h-64 items-center justify-center">
          <QueryState isLoading={graph.isLoading} isError={graph.isError} error={graph.error} />
        </Card>
      ) : (
        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader>
              <CardTitle>The national material master, so far</CardTitle>
              <CardDescription className="max-w-3xl">
                Every dark centre is a national code. Every dot around it is one CPSE&apos;s own
                material code that resolved into it, coloured by the organisation it came from.
                Hover to isolate a cluster, click to read what those codes actually said.
              </CardDescription>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {orgs.map((o) => (
                  <Badge key={o} variant="outline" className="gap-1.5 font-mono text-[11px]">
                    <span className="h-2 w-2 rounded-full" style={{ background: orgColour(o) }} />
                    {o}
                  </Badge>
                ))}
                <Badge variant="outline" className="gap-1.5 font-mono text-[11px]">
                  <span className="h-2 w-2 rounded-full border-2 border-muted-foreground bg-background" />
                  substitute
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <ClusterMap
                clusters={clusters}
                selected={selected?.canonical_id ?? null}
                onSelect={setPicked}
              />
              <Separator className="my-4" />
              <p className="text-xs text-muted-foreground">
                Showing the {graph.data.shown} identities spanning the most organisations, of{' '}
                {graph.data.total_clusters} built so far.
              </p>
            </CardContent>
          </Card>

          {selected && (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <ClusterDetail cluster={selected} />
              <Card>
                <CardHeader>
                  <CardTitle>Why this is hard</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
                  <p>
                    Nothing in those descriptions matches. One writes{' '}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">M20X40</code>,
                    another{' '}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">M20 x 40mm</code>,
                    a third{' '}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">DIA 20MM; LG 40MM</code>.
                    A text comparison finds nothing in common.
                  </p>
                  <p>
                    Each CPSE has been buying the same bolt under its own code for years, and
                    neither system had any way to know.
                  </p>
                  <Separator />
                  <p>
                    The match is made on extracted attributes rather than on the words: diameter,
                    length, property class, standard. Every value carries the substring that
                    proved it, so a reviewer checks the working rather than trusting a score.
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
