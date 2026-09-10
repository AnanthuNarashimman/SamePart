import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'

// Per attribute, which organisations independently supplied evidence for the same value.
//
// A filled dot means that CPSE's own description carried this fact. A hollow one means it
// stated something different, and the value beside it says what. An empty slot means it never
// said. That makes agreement, disagreement and silence three visibly different things, where
// prose would flatten all three into "we extract attributes".
export function EvidenceFingerprint({
  cluster,
  order,
  orgs,
  lit,
  onLight,
}: {
  cluster: GraphCluster
  order: string[]
  orgs: string[]
  lit: string | null
  onLight: (key: string | null) => void
}) {
  const cols = order.filter((k) =>
    cluster.members.some((m) => m.attributes.find((a) => a.key === k)?.value != null),
  )
  const label = (k: string) =>
    cluster.members.map((m) => m.attributes.find((a) => a.key === k)?.label).find(Boolean) ?? k

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-4">
      {cols.map((key) => {
        // The agreed value is simply the one most sources state.
        const tally = new Map<string, number>()
        for (const m of cluster.members) {
          const v = m.attributes.find((a) => a.key === key)?.value
          if (v != null) tally.set(String(v), (tally.get(String(v)) ?? 0) + 1)
        }
        const agreed = [...tally.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]

        return (
          <div
            key={key}
            onMouseEnter={() => onLight(key)}
            onMouseLeave={() => onLight(null)}
            className={`rounded-lg px-3 py-2 transition-colors ${
              lit === key ? 'bg-amber-50' : 'bg-transparent'
            }`}
          >
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {label(key).replace('Nominal thread ', '').replace('Nominal ', '')
                .replace(' under head', '').replace('Property class or ', '')
                .replace('Governing specification', 'standard')}
            </p>
            <p className="mt-0.5 font-mono text-lg leading-tight text-foreground">{agreed}</p>

            <ul className="mt-2 flex flex-col gap-1">
              {orgs.map((o) => {
                const stated = cluster.members
                  .filter((m) => m.org_code === o)
                  .map((m) => m.attributes.find((a) => a.key === key)?.value)
                  .filter((v) => v != null)
                  .map(String)
                const has = stated.length > 0
                const agrees = stated.includes(String(agreed))
                const other = has && !agrees ? stated[0] : null
                return (
                  <li key={o} className="flex items-center gap-1.5 font-mono text-[10px]">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full border"
                      style={{
                        background: agrees ? orgColour(o) : 'transparent',
                        borderColor: has ? orgColour(o) : '#d6d3d1',
                      }}
                    />
                    <span className={has ? 'text-muted-foreground' : 'text-muted-foreground/40'}>
                      {o}
                    </span>
                    {other && <span className="text-amber-700">{other}</span>}
                    {!has && <span className="text-muted-foreground/40">—</span>}
                  </li>
                )
              })}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
