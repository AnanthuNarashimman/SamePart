import type { GraphCluster, GraphMember } from '../../api/types'
import { orgColour } from '../insights/tokens'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

// The proof view: original description on the left, extracted attributes across.
//
// This is where the technical claim becomes visible rather than asserted. The descriptions
// share almost no words. The attribute columns are identical. Hovering a value lights up the
// exact substring it came from in every row at once, which is a far better argument for
// evidence provenance than a paragraph explaining that we have it.

const HIDDEN_WHEN_EMPTY = new Set(['thread_pitch_mm'])

function Marked({ text, mark }: { text: string; mark: string | null }) {
  if (!mark) return <>{text}</>
  const at = text.toUpperCase().indexOf(mark.toUpperCase())
  if (at < 0) return <>{text}</>
  return (
    <>
      {text.slice(0, at)}
      <mark className="rounded bg-amber-200/70 px-0.5 text-foreground">
        {text.slice(at, at + mark.length)}
      </mark>
      {text.slice(at + mark.length)}
    </>
  )
}

function value(m: GraphMember, key: string) {
  return m.attributes.find((a) => a.key === key)
}

export function EvidenceInspector({
  cluster,
  order,
  lit,
  onLight,
}: {
  cluster: GraphCluster
  order: string[]
  lit: string | null
  onLight: (key: string | null) => void
}) {
  const rows = cluster.members
  const keys = order.filter(
    (k) => !(HIDDEN_WHEN_EMPTY.has(k) && rows.every((r) => value(r, k)?.value == null)),
  )
  const label = (k: string) =>
    rows.map((r) => value(r, k)?.label).find(Boolean) ?? k
  const short = (k: string) =>
    label(k).replace('Nominal thread ', '').replace('Nominal ', '')
      .replace(' under head', '').replace('Property class or ', '')
      .replace('Governing specification', 'standard').replace('Surface ', '')

  return (
    <Card>
      <CardHeader>
        <CardTitle>The words barely match. The attributes do.</CardTitle>
        <CardDescription>
          {rows.length} codes from {cluster.orgs.length} CPSEs. Hover any value to light up the
          exact words it was read from, in every row at once.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  source
                </th>
                <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  original description
                </th>
                {keys.map((k) => (
                  <th key={k}
                      className="py-2 pr-3 font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {short(k)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.record_id} className="border-b border-border/60 align-top">
                  <td className="py-2.5 pr-4">
                    <span className="flex items-center gap-1.5 font-mono text-[11px]">
                      <span className="h-2 w-2 shrink-0 rounded-full"
                            style={{ background: orgColour(m.org_code) }} />
                      {m.org_code}
                    </span>
                  </td>
                  <td className="max-w-[26rem] py-2.5 pr-4 font-mono text-[11px] leading-snug text-muted-foreground">
                    <Marked
                      text={m.raw_description}
                      mark={lit ? (value(m, lit)?.evidence ?? null) : null}
                    />
                  </td>
                  {keys.map((k) => {
                    const a = value(m, k)
                    const missing = a?.value == null
                    return (
                      <td
                        key={k}
                        onMouseEnter={() => onLight(k)}
                        onMouseLeave={() => onLight(null)}
                        className={`cursor-default py-2.5 pr-3 font-mono text-[11px] transition-colors ${
                          lit === k ? 'bg-amber-50' : ''
                        } ${missing ? 'text-muted-foreground/50' : 'font-medium text-foreground'}`}
                      >
                        {missing ? '—' : String(a?.value)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Separator className="my-4" />

        <div className="rounded-lg bg-primary px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-primary-foreground/60">
            ↓ resolves to
          </p>
          <p className="mt-1 font-mono text-sm text-primary-foreground">
            {cluster.standardised_short}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-primary-foreground/60">
            {cluster.national_code}
          </p>
        </div>

        {cluster.alternatives.length > 0 && (
          <div className="mt-4">
            <Separator className="mb-3" />
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="outline" className="font-mono text-[10px]">
                compatible, not identical
              </Badge>
            </div>
            {/* Kept out of the identity on purpose. Entity resolution and engineering
                substitution are different questions and the interface should say so. */}
            {cluster.alternatives.map((a) => (
              <div key={a.record_id} className="mb-3 border-l-2 border-dashed border-border pl-3">
                <p className="font-mono text-[11px] text-foreground">{a.raw_description}</p>
                <p className="font-mono text-[10px] text-muted-foreground">
                  {a.org_code} · {a.source_code}
                </p>
                {a.condition && (
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    <span className="font-medium text-foreground">Safe only when: </span>
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
