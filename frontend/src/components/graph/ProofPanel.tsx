import type { GraphCluster } from '../../api/types'
import { orgColourDark } from '../insights/tokens'

// The proof, on a dark analytical surface, pinned beside the matrix.
//
// Dark for two reasons, neither decorative. The page around it is pale and low-contrast, and
// the one thing that must not read as pale is the claim the whole product rests on. And a
// reader who clicks a row needs the answer to feel like a different kind of object from the
// list they clicked it in — a panel, not another row.
//
// Deep green rather than black. Black belongs to nothing in this product; #0d2a1a is the brand
// hue taken almost to the floor, so the panel reads as part of the same system rather than as
// a terminal window dropped onto the page. Checked rather than picked: all four CPSE colours
// clear 3:1 against it (worst 3.97, CPCL) and white text sits at 15.4:1. A lighter, more
// obviously green ground was tried first and failed — CPCL fell to 2.97.
//
// Each attribute is a card rather than a line of text, because an attribute is a unit: a name,
// one agreed value, and four independent votes on it. Spread across a grid of loose text those
// three things stop reading as one fact.

/** The panel ground. Not black: the brand hue taken almost to the floor. */
const GROUND = '#0d2a1a'

const SHORTEN = (s: string) =>
  s.replace('Nominal thread ', '').replace('Nominal ', '').replace(' under head', '')
    .replace('Property class or ', '').replace('Governing specification', 'standard')

export function ProofPanel({
  cluster,
  order,
  orgs,
  lit,
  onLight,
  pinned,
  onPin,
}: {
  cluster: GraphCluster
  order: string[]
  orgs: string[]
  lit: string | null
  onLight: (key: string | null) => void
  pinned: string | null
  onPin: (key: string | null) => void
}) {
  const cols = order.filter((k) =>
    cluster.members.some((m) => m.attributes.find((a) => a.key === k)?.value != null),
  )
  const label = (k: string) =>
    cluster.members.map((m) => m.attributes.find((a) => a.key === k)?.label).find(Boolean) ?? k

  const [head, ...rest] = (cluster.standardised_short ?? cluster.canonical_id).split(';')
  const subs = cluster.alternatives.length

  return (
    <div className="overflow-hidden rounded-2xl text-stone-100 shadow-sm"
         style={{ background: GROUND }}>
      <div className="px-5 pt-5 pb-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-emerald-200/45">
          proving this identity
        </p>
        <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-white">{head}</h2>
        <p className="mt-1 font-mono text-base text-emerald-50/80">
          {rest.join(' · ').trim()}
        </p>

        <div className="mt-3.5 flex flex-wrap items-center gap-1.5">
          <span className="rounded-md bg-white/10 px-2 py-1 font-mono text-[11px] text-stone-200">
            {cluster.national_code}
          </span>
          <span className="rounded-md bg-white/5 px-2 py-1 font-mono text-[11px] text-emerald-50/60">
            {cluster.orgs.length} CPSEs
          </span>
          <span className="rounded-md bg-white/5 px-2 py-1 font-mono text-[11px] text-emerald-50/60">
            {cluster.members.length} codes
          </span>
          {subs > 0 && (
            <span className="rounded-md border border-dashed border-white/25 px-2 py-1
                             font-mono text-[11px] text-emerald-50/60">
              {subs} substitute{subs > 1 ? 's' : ''} kept separate
            </span>
          )}
        </div>
      </div>

      <div className="border-t border-white/10 px-5 py-4">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-emerald-200/45">
          independent evidence, by attribute
        </p>

        <div className="grid grid-cols-2 gap-2">
          {cols.map((key) => {
            // The agreed value is simply the one most sources state.
            const tally = new Map<string, number>()
            for (const m of cluster.members) {
              const v = m.attributes.find((a) => a.key === key)?.value
              if (v != null) tally.set(String(v), (tally.get(String(v)) ?? 0) + 1)
            }
            const agreed = [...tally.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
            const isLit = lit === key
            const isPinned = pinned === key

            // A CPSE with several codes can state the agreed value on one and a variant on
            // another. That is agreement plus a variant, not disagreement, and conflating the
            // two produced a card reading "ISO4017" over "BPCL said DIN933" for a CPSE whose
            // own catalogue contained ISO4017. So the three states are kept apart: stated the
            // agreed value, stated only something else, or never said.
            const votes = orgs.map((o) => {
              const stated = cluster.members
                .filter((m) => m.org_code === o)
                .map((m) => m.attributes.find((a) => a.key === key)?.value)
                .filter((v) => v != null)
                .map(String)
              const variants = [...new Set(stated.filter((v) => v !== agreed))]
              return {
                org: o,
                has: stated.length > 0,
                agrees: stated.includes(String(agreed)),
                variants,
              }
            })
            const dissent = votes.filter((v) => v.has && !v.agrees)
            const variantOrgs = votes.filter((v) => v.agrees && v.variants.length > 0)

            return (
              <button
                key={key}
                type="button"
                onMouseEnter={() => onLight(key)}
                onMouseLeave={() => onLight(null)}
                onFocus={() => onLight(key)}
                onBlur={() => onLight(null)}
                onClick={() => onPin(isPinned ? null : key)}
                aria-pressed={isPinned}
                // flex-col because a button centres its contents vertically by default, which
                // left the shorter cards floating against taller neighbours in the same row.
                className={`flex flex-col items-stretch rounded-lg border p-2.5 text-left
                            transition-colors
                            focus-visible:outline focus-visible:outline-2
                            focus-visible:outline-offset-2 focus-visible:outline-white/60 ${
                  isPinned
                    ? 'border-amber-300/70 bg-amber-300/15'
                    : isLit
                      ? 'border-white/25 bg-white/[0.08]'
                      : 'border-white/10 bg-white/[0.045] hover:bg-white/[0.08]'
                }`}
              >
                <p className="font-mono text-[9.5px] uppercase tracking-wider text-emerald-200/45">
                  {SHORTEN(label(key))}
                </p>
                <p className="mt-0.5 font-mono text-lg leading-tight text-white">{agreed}</p>

                <ul className="mt-2 flex flex-wrap gap-x-2.5 gap-y-1">
                  {votes.map((v) => (
                    <li key={v.org} className="flex items-center gap-1 font-mono text-[9.5px]">
                      <span
                        className="h-[7px] w-[7px] shrink-0 rounded-full border"
                        style={{
                          background: v.agrees ? orgColourDark(v.org) : 'transparent',
                          borderColor: v.has ? orgColourDark(v.org) : 'rgba(255,255,255,0.22)',
                        }}
                      />
                      <span className={v.has ? 'text-emerald-50/60' : 'text-emerald-200/30'}>{v.org}</span>
                    </li>
                  ))}
                </ul>

                {/* A disagreement is the most interesting thing on the card, so it is spelled
                    out rather than left as a hollow dot the reader has to decode. A variant
                    held alongside the agreed value is a different and equally interesting
                    fact — it is the DIN-versus-ISO case the dictionary exists to reconcile —
                    so it gets its own line rather than being called a conflict. */}
                {(dissent.length > 0 || variantOrgs.length > 0) && (
                  <div className="mt-2 space-y-1 border-t border-white/10 pt-1.5 font-mono text-[9.5px]">
                    {dissent.length > 0 && (
                      <p className="text-amber-300/90">
                        {dissent.map((v) => `${v.org} says ${v.variants[0]}`).join(' · ')}
                      </p>
                    )}
                    {variantOrgs.length > 0 && (
                      <p className="text-emerald-50/60">
                        also listed as {[...new Set(variantOrgs.flatMap((v) => v.variants))].join(', ')}
                        {' by '}
                        {variantOrgs.map((v) => v.org).join(', ')}
                      </p>
                    )}
                  </div>
                )}
              </button>
            )
          })}
        </div>

        <p className="mt-3 text-[11px] leading-relaxed text-emerald-200/45">
          A filled dot means that CPSE&apos;s own description carried this fact independently.
          Hollow means it stated something different. Hover a card to light the exact words in
          the source text below; click to hold it.
        </p>
      </div>
    </div>
  )
}
