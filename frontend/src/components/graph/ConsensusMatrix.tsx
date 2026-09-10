import { useMemo, useRef, useState } from 'react'
import type { GraphCluster } from '../../api/types'
import { orgColour } from '../insights/tokens'
import { HoverCard, useHoverCard } from '../shared/HoverCard'
import { Pager, usePaged } from '../shared/Paginated'

// Agreement, as a matrix. One row per national identity, one column per CPSE.
//
// This replaces a Sankey, and the reason is worth writing down so nobody rebuilds it. A Sankey
// encodes flow between stages. There are no stages here — there is a set of organisations and
// a set of identities, and the question is which of them agree. That is a matrix, and forcing
// it through a flow diagram meant forty ribbons crossing to say something a grid says in one
// glance. The ribbons were dramatic and answered none of the four questions a reader actually
// has: which identities matter, how many organisations agree, what matched, and why.
//
// So each cell answers "did this CPSE contribute a code to this identity, and how many".
// Area, not radius, carries the count, because a reader compares blobs by area and doubling
// the radius quadruples the ink for twice the codes.

const R_MIN = 4.5
const R_MAX = 11

type Sort = 'consensus' | 'codes' | 'name'

export function ConsensusMatrix({
  clusters,
  orgs,
  selected,
  onSelect,
}: {
  clusters: GraphCluster[]
  orgs: string[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  const [sort, setSort] = useState<Sort>('consensus')
  const { anchor, show, hide } = useHoverCard()

  const rows = useMemo(() => {
    const built = clusters.map((c) => {
      const merged: Record<string, number> = {}
      for (const m of c.members) merged[m.org_code] = (merged[m.org_code] ?? 0) + 1
      const subs: Record<string, number> = {}
      for (const a of c.alternatives) subs[a.org_code] = (subs[a.org_code] ?? 0) + 1
      return {
        cluster: c,
        merged,
        subs,
        codes: c.members.length,
        consensus: Object.keys(merged).length,
        subTotal: c.alternatives.length,
        // Drop the family head, whatever it is. This read `.replace('BOLT, HEX HEAD; ', '')`,
        // so with four families every bearing row rendered as "BEARING, DEEP GROOVE BALL;
        // 12MM; SERIES…" and truncated away the only part that differed. The head names the
        // family, which the reader already knows; the tail is the identity.
        short: (c.standardised_short ?? c.canonical_id).split('; ').slice(1).join('; ')
               || (c.standardised_short ?? c.canonical_id),
        family: (c.standardised_short ?? '').split(';')[0],
      }
    })
    const by = {
      consensus: (a: typeof built[number], b: typeof built[number]) =>
        b.consensus - a.consensus || b.codes - a.codes,
      codes: (a: typeof built[number], b: typeof built[number]) =>
        b.codes - a.codes || b.consensus - a.consensus,
      name: (a: typeof built[number], b: typeof built[number]) => a.short.localeCompare(b.short),
    }
    return [...built].sort(by[sort])
  }, [clusters, sort])

  // Twelve to a page: enough to compare rows against each other, short enough that the
  // proof panel beside it stays level with the table rather than floating past its end.
  const paged = usePaged(rows, 12)
  const anySubs = rows.some((r) => r.subTotal > 0)
  const maxCodes = Math.max(...rows.map((r) => r.codes), 1)
  const maxCell = Math.max(...rows.flatMap((r) => Object.values(r.merged)), 1)
  // Area proportional to count, so two codes look twice as heavy as one rather than four times.
  const radius = (n: number) => R_MIN + (R_MAX - R_MIN) * Math.sqrt((n - 1) / Math.max(maxCell - 1, 1))

  const grid = {
    display: 'grid',
    gridTemplateColumns: `minmax(0,1fr) repeat(${orgs.length}, 54px) ${anySubs ? '58px ' : ''}150px`,
    alignItems: 'center',
  } as const

  const listRef = useRef<HTMLUListElement>(null)
  const onKey = (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const buttons = Array.from(listRef.current?.querySelectorAll('button') ?? [])
    const at = buttons.indexOf(document.activeElement as HTMLButtonElement)
    const next = buttons[at + (e.key === 'ArrowDown' ? 1 : -1)]
    if (next) {
      next.focus()
      next.click()
    }
  }

  const SortBtn = ({ k, children }: { k: Sort; children: React.ReactNode }) => (
    <button
      type="button"
      onClick={() => setSort(k)}
      aria-pressed={sort === k}
      className={`font-mono text-[10px] uppercase tracking-widest transition-colors ${
        sort === k ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
    </button>
  )

  return (
    <div className="rounded-2xl border border-stone-100 bg-white shadow-sm">
      <div style={grid} className="border-b border-stone-100 px-5 py-2.5">
        <SortBtn k="name">national identity</SortBtn>
        {orgs.map((o) => (
          <span key={o} className="text-center font-mono text-[10px] font-medium tracking-wide"
                style={{ color: orgColour(o) }}>
            {o}
          </span>
        ))}
        {anySubs && (
          <span className="text-center font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            sub
          </span>
        )}
        <div className="flex items-center justify-end gap-2">
          <SortBtn k="consensus">agree</SortBtn>
          <span className="text-stone-200">·</span>
          <SortBtn k="codes">codes</SortBtn>
        </div>
      </div>

      <ul ref={listRef} onKeyDown={onKey} className="divide-y divide-stone-100">
        {paged.slice.map((r) => {
          const isSel = selected === r.cluster.canonical_id
          return (
            <li key={r.cluster.canonical_id}>
              <button
                type="button"
                style={grid}
                onClick={() => onSelect(r.cluster.canonical_id)}
                aria-pressed={isSel}
                className={`w-full border-l-[3px] px-5 py-3 text-left transition-colors
                            focus-visible:outline focus-visible:outline-2
                            focus-visible:-outline-offset-2 focus-visible:outline-stone-900 ${
                  isSel
                    ? 'border-stone-900 bg-stone-900/[0.055]'
                    : 'border-transparent hover:bg-stone-100/70'
                }`}
              >
                <span className="flex min-w-0 flex-col pr-4">
                  <span
                    className={`truncate font-mono text-[13px] ${
                      isSel ? 'font-semibold text-stone-900' : 'font-medium text-stone-700'
                    }`}
                  >
                    {r.short}
                  </span>
                  {r.family && (
                    <span className="truncate font-mono text-[10px] uppercase tracking-wide
                                     text-stone-400">
                      {r.family}
                    </span>
                  )}
                </span>

                {orgs.map((o) => {
                  const n = r.merged[o] ?? 0
                  const sub = r.subs[o] ?? 0
                  // Dot area is a comparison, not a quantity: a reader can see that one CPSE
                  // contributed more than another but cannot read "three" off a circle. The
                  // tooltip supplies the number the encoding deliberately does not.
                  // A real hover layer rather than the browser's `title`, which takes about a
                  // second to appear, cannot be styled, and shows one line of grey text. On a
                  // grid of a hundred and sixty cells that is the difference between a chart
                  // you can interrogate and one you can only look at.
                  const reading =
                    n > 0
                      ? `${o} folded in ${n} source code${n === 1 ? '' : 's'}` +
                        (sub > 0 ? `, and holds ${sub} substitute${sub === 1 ? '' : 's'}` : '')
                      : sub > 0
                        ? `${o} has no code in this identity, but holds ${sub} substitute${
                            sub === 1 ? '' : 's'} kept separate from it`
                        : `${o} has no code for this material`

                  const card = (
                    <>
                      <span className="flex items-center gap-1.5 font-medium text-stone-900">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full"
                              style={{ background: orgColour(o) }} />
                        {o}
                      </span>
                      <span className="mt-1 block text-[11px] leading-relaxed text-stone-600">
                        {reading}
                      </span>
                      <span className="mt-1.5 block border-t border-stone-100 pt-1.5 font-mono
                                       text-[10px] text-stone-400">
                        {r.short}
                      </span>
                    </>
                  )

                  return (
                    <span key={o} className="flex justify-center">
                      <svg
                        width="26" height="26" className="overflow-visible"
                        onMouseEnter={(e) => show(e, card)}
                        onMouseMove={(e) => show(e, card)}
                        onMouseLeave={hide}
                      >
                        {n > 0 ? (
                          <circle cx="13" cy="13" r={radius(n)} fill={orgColour(o)} />
                        ) : sub > 0 ? (
                          // A substitute is not a merge. It gets an outline, never a fill,
                          // because "interchangeable under conditions" and "the same material"
                          // are different claims and must not share a mark.
                          <circle cx="13" cy="13" r={R_MIN + 1.5} fill="none"
                                  stroke={orgColour(o)} strokeWidth="1.4" strokeDasharray="2.5 2" />
                        ) : (
                          <circle cx="13" cy="13" r="1.6" fill="#e7e5e4" />
                        )}
                        {/* A hit area the size of the cell, so a one-code dot is as easy to
                            hover as an eight-code one. */}
                        <circle cx="13" cy="13" r="13" fill="transparent" />
                      </svg>
                      <span className="sr-only">{reading}</span>
                    </span>
                  )
                })}

                {anySubs && (
                  <span className="text-center font-mono text-[11px] text-stone-400">
                    {r.subTotal || '—'}
                  </span>
                )}

                <span className="flex items-center justify-end gap-2.5">
                  {r.consensus === orgs.length ? (
                    <span className="rounded-full bg-stone-900 px-1.5 py-0.5 font-mono text-[9.5px]
                                     font-medium tracking-wide text-white">
                      {orgs.length}-WAY
                    </span>
                  ) : (
                    <span className="flex items-center gap-[3px]" aria-hidden>
                      {orgs.map((_, i) => (
                        <span key={i}
                              className={`h-[7px] w-[7px] rounded-[1px] ${
                                i < r.consensus ? 'bg-stone-500' : 'bg-stone-200'
                              }`} />
                      ))}
                    </span>
                  )}
                  <span className="sr-only">{r.consensus} of {orgs.length} CPSEs agree</span>
                  {/* The bar is total codes collapsed — the compression this one row bought. */}
                  <span className="relative h-3 w-14 overflow-hidden rounded-sm bg-stone-150 bg-stone-100">
                    <span
                      className={`absolute inset-y-0 left-0 rounded-sm ${
                        isSel ? 'bg-stone-900' : 'bg-stone-700'
                      }`}
                      style={{ width: `${(r.codes / maxCodes) * 100}%` }}
                    />
                  </span>
                  <span className="w-5 text-right font-mono text-[13px] font-semibold tabular-nums text-stone-900">
                    {r.codes}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <Pager
        page={paged.page} pages={paged.pages} from={paged.from} to={paged.to}
        total={paged.total} unit="identities" onPage={paged.setPage}
        className="border-t border-stone-100 px-5 py-2.5"
      />

      <HoverCard anchor={anchor} />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 border-t border-stone-100 px-5 py-2.5
                      text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <svg width="18" height="12" aria-hidden><circle cx="9" cy="6" r="5" fill="#57534e" /></svg>
          filled = codes merged, sized by how many
        </span>
        {anySubs && (
          <span className="flex items-center gap-1.5">
            <svg width="18" height="12" aria-hidden>
              <circle cx="9" cy="6" r="5" fill="none" stroke="#57534e" strokeWidth="1.4"
                      strokeDasharray="2.5 2" />
            </svg>
            outline = substitute only, never merged
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <svg width="18" height="12" aria-hidden><circle cx="9" cy="6" r="1.6" fill="#d6d3d1" /></svg>
          no code at this CPSE
        </span>
      </div>
    </div>
  )
}
