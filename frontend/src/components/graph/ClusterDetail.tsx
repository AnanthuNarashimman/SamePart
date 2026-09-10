import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

// One cluster, opened up. This is where the argument lives: several CPSEs describing the
// same physical item in ways no string comparison would ever reconcile, all resolving to one
// national code.
//
// The raw descriptions are the point. The previous version captioned every node "merged —
// all attributes agree", which states the answer and hides the problem.
export function ClusterDetail({ cluster }: { cluster: GraphCluster }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{cluster.members.length} codes, one material</CardTitle>
        <CardDescription>
          Across {cluster.orgs.length} CPSEs. None of them could see the others.
        </CardDescription>
        <Badge variant="outline" className="w-fit font-mono text-[11px]">
          {cluster.national_code}
        </Badge>
      </CardHeader>
      <CardContent>
      {/* The messy side, in full. Each line is what one organisation actually wrote. */}
      <ul className="mb-1 flex flex-col divide-y divide-border">
        {cluster.members.map((m) => (
          <li key={m.record_id} className="flex items-start gap-3 py-2">
            <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: orgColour(m.org_code) }} />
            <div className="min-w-0 flex-1">
              <p className="font-mono text-[12px] leading-snug text-foreground">
                {m.raw_description}
              </p>
              <p className="font-mono text-[10px] text-muted-foreground">
                {m.org_code} · {m.source_code}
              </p>
            </div>
          </li>
        ))}
      </ul>

      {/* Everything above resolves to this. */}
      <div className="mt-4 rounded-lg bg-primary px-4 py-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-primary-foreground/60">
          resolves to
        </p>
        <p className="mt-1 font-mono text-[13px] text-primary-foreground">
          {cluster.standardised_short}
        </p>
        <p className="mt-0.5 font-mono text-[11px] text-primary-foreground/60">
          {cluster.national_code}
        </p>
      </div>

      {cluster.alternatives.length > 0 && (
        <div className="mt-4">
          <Separator className="mb-3" />
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            linked, not merged
          </p>
          {cluster.alternatives.map((a) => (
            <div key={a.record_id} className="mb-2">
              <p className="font-mono text-[11px] text-foreground">{a.raw_description}</p>
              {a.condition && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                  {a.condition}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
      </CardContent>
    </Card>
  )
}
