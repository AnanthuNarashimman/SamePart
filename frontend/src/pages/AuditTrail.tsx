import { useState } from 'react'
import { useAuditTrail, useAuditVerify } from '../api/audit'
import type { AuditEvent } from '../api/types'
import { Pager, usePaged } from '../components/shared/Paginated'
import { QueryState } from '../components/shared/QueryState'

// The decision log, as a page.
//
// It existed as an endpoint and inside every passport, and the dashboard walked its hash chain
// and reported pass or fail — but nothing showed the events themselves, so the claim "every
// decision is recorded and signed by the seat that made it" could only be demonstrated with
// curl. This is the screen that claim points at: newest first, who, what, which pair or code,
// and a line at the top saying whether the chain still verifies.

const ACTION_LABEL: Record<string, string> = {
  approve_same: 'Merged as the same material',
  approve_alternative: 'Linked as a substitute',
  approve_different: 'Confirmed different',
  reject: 'Rejected the proposal',
  request_info: 'Asked for information',
  attributes_supplied: 'Answered a question',
  declared_unresolvable: 'Marked a blank unresolvable',
  mapping_reversed: 'Reversed a mapping',
  family_loaded: 'Added a material family',
  family_replaced: 'Replaced a material family',
  family_removed: 'Removed a material family',
}

const ACTION_TONE: Record<string, string> = {
  approve_same: 'bg-brand-100 text-brand-900',
  approve_alternative: 'bg-khaki-100 text-khaki-800',
  approve_different: 'bg-stone-100 text-stone-700',
  reject: 'bg-rose-50 text-rose-700',
  attributes_supplied: 'bg-sky-50 text-sky-800',
  declared_unresolvable: 'bg-stone-100 text-stone-700',
  mapping_reversed: 'bg-rose-50 text-rose-700',
  request_info: 'bg-sky-50 text-sky-800',
  family_loaded: 'bg-brand-100 text-brand-900',
  family_replaced: 'bg-khaki-100 text-khaki-800',
  family_removed: 'bg-rose-50 text-rose-700',
}

// Stewards carry their organisation's colour so a mixed page reads at a glance.
const ACTOR_TONE: Record<string, string> = {
  'BPCL-steward': 'bg-[#3987e5] text-white',
  'CPCL-steward': 'bg-[#e8703c] text-white',
  'IOCL-steward': 'bg-[#24b985] text-white',
  'NTPC-steward': 'bg-[#e0a119] text-white',
  'national-approver': 'bg-stone-900 text-white',
}

function when(iso: string): string {
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`)
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function detail(e: AuditEvent): string {
  const p = e.payload ?? {}
  if (e.action === 'attributes_supplied' && p.applied) {
    const filled = Object.entries(p.applied as Record<string, string>)
      .map(([k, v]) => `${k} = ${v}`).join(', ')
    return `${filled} · ${p.pairs_reevaluated ?? 0} pairs re-decided`
  }
  if (e.action === 'declared_unresolvable' && p.keys) {
    return `${(p.keys as string[]).join(', ')}${p.reason ? ` · ${p.reason}` : ''}`
  }
  if (e.action === 'mapping_reversed' && p.reason) return String(p.reason)
  if (e.action === 'family_removed' && p.family) {
    return `${p.label ?? p.family}${p.records_removed ? ` · ${p.records_removed} records removed with it` : ''}`
  }
  if ((e.action === 'family_loaded' || e.action === 'family_replaced') && p.family) {
    return `${p.label ?? p.family} · ${p.attributes} attributes, ${p.gates} gates`
  }
  if (p.condition) return String(p.condition)
  return e.summary
}

export function AuditTrail() {
  const [actor, setActor] = useState<string>('')
  const [action, setAction] = useState<string>('')
  const trail = useAuditTrail({ limit: 500, actor: actor || undefined, action: action || undefined })
  const chain = useAuditVerify()
  // Fifteen to a page: enough to see a session's worth of work, few enough to read.
  const paged = usePaged(trail.data?.items ?? [], 15)

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Audit trail</h1>
          <p className="text-sm text-stone-400">
            {trail.data
              ? <>{trail.data.total.toLocaleString('en-IN')} decisions, append-only · each one signed by the seat that made it</>
              : 'Loading…'}
          </p>
        </div>
        {chain.data && (
          <div
            className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${
              chain.data.intact ? 'bg-stone-900 text-white' : 'bg-rose-600 text-white'
            }`}
            title={chain.data.intact ? 'Every event still hashes to what was written' : chain.data.reason}
          >
            <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${chain.data.intact ? 'bg-brand-500' : 'bg-white'}`} />
            {chain.data.intact
              ? `Hash chain intact · ${chain.data.events.toLocaleString('en-IN')} events verified`
              : `Chain broken at event ${chain.data.broken_at}`}
          </div>
        )}
      </header>

      {trail.data && (
        <div className="mb-5 flex flex-wrap gap-3">
          <label className="text-xs text-stone-500">
            <span className="mb-1 block font-medium">Who</span>
            <select
              value={actor}
              onChange={(e) => { setActor(e.target.value); paged.setPage(0) }}
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
            >
              <option value="">Everyone</option>
              {Object.entries(trail.data.by_actor).sort().map(([a, n]) => (
                <option key={a} value={a}>{a} ({n.toLocaleString('en-IN')})</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-stone-500">
            <span className="mb-1 block font-medium">What</span>
            <select
              value={action}
              onChange={(e) => { setAction(e.target.value); paged.setPage(0) }}
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
            >
              <option value="">Every action</option>
              {Object.entries(trail.data.by_action).sort().map(([a, n]) => (
                <option key={a} value={a}>{ACTION_LABEL[a] ?? a} ({n.toLocaleString('en-IN')})</option>
              ))}
            </select>
          </label>
        </div>
      )}

      {!trail.data ? (
        <QueryState isLoading={trail.isLoading} isError={trail.isError} error={trail.error} loadingLabel="Reading the trail" />
      ) : (
        <div className="rounded-2xl border border-stone-100 bg-white shadow-sm">
          <ol className="divide-y divide-stone-100">
            {paged.slice.map((e) => (
              <li key={e.id} className="grid grid-cols-[3.5rem_9rem_1fr] items-start gap-3 px-5 py-3 sm:grid-cols-[3.5rem_9.5rem_11rem_1fr]">
                <span className="pt-0.5 font-mono text-[11px] text-stone-400">#{e.id}</span>
                <span className="pt-0.5 font-mono text-[11px] text-stone-500">{when(e.at)}</span>
                <span>
                  <span className={`inline-block rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold ${ACTOR_TONE[e.actor] ?? 'bg-stone-200 text-stone-700'}`}>
                    {e.actor}
                  </span>
                </span>
                <span className="min-w-0 col-span-3 sm:col-span-1">
                  <span className={`mr-2 inline-block rounded-md px-1.5 py-0.5 text-[11px] font-medium ${ACTION_TONE[e.action] ?? 'bg-stone-100 text-stone-700'}`}>
                    {ACTION_LABEL[e.action] ?? e.action}
                  </span>
                  <span className="text-xs text-stone-600">{detail(e)}</span>
                  {(e.canonical_id || e.match_id) && (
                    <span className="ml-2 font-mono text-[11px] text-stone-400">
                      {e.canonical_id ?? ''}{e.canonical_id && e.match_id ? ' · ' : ''}{e.match_id ? `pair #${e.match_id}` : ''}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ol>
          <Pager
            page={paged.page}
            pages={paged.pages}
            from={paged.from}
            to={paged.to}
            total={paged.total}
            unit="events"
            onPage={paged.setPage}
            className="border-t border-stone-100 px-5 py-3"
          />
        </div>
      )}

      <p className="mt-4 text-[11px] leading-relaxed text-stone-400">
        Each event carries the hash of the one before it. Edit, delete or reorder any row and
        the verification above fails at that row; the check is open to anyone, including
        someone who does not trust the operator.
      </p>
    </div>
  )
}
