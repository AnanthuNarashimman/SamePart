import { useState } from 'react'
import { useOrgs } from '../api/catalogue'
import { useFamilies } from '../api/catalogue'
import { useCheck } from '../api/prevention'
import type { CheckResult } from '../api/types'
import { MatchComparison } from '../components/shared/MatchComparison'
import { QueryState } from '../components/shared/QueryState'
import { useActor } from '../lib/actor'

// Single-record check reusing the same pipeline against the full canonical set — no queue,
// no grouping, one session, one verdict. Per knowledge/08-ranked-additions.md, arguably the
// highest-ROI feature in the system: it stops a duplicate before a code is minted.
export function DuplicateCheck() {
  const orgs = useOrgs()
  const check = useCheck()
  const families = useFamilies()
  const [family, setFamily] = useState('')
  // The API used to default this to bolts, so pasting a gasket description here
  // matched none of the bolt patterns, found no duplicate, and cheerfully said the
  // code was safe to create -- the one answer this page must never give wrongly.
  const effectiveFamily = family || families.data?.[0]?.family || ''

  const [orgCode, setOrgCode] = useState<string | null>(null)
  const [description, setDescription] = useState('')

  // A steward acts for their own organisation and cannot choose another; the national
  // approver may act for any.
  const { actor } = useActor()
  const lockedOrg = actor.role === 'steward' ? actor.org : null
  const effectiveOrgCode = lockedOrg ?? orgCode ?? orgs.data?.[0]?.code ?? ''

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Duplicate-prevention check</h1>
        <p className="text-sm text-stone-400">
          Check a description against the whole canonical set before a new material code is minted
        </p>
      </header>

      <div className="mb-5 rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="w-full sm:w-56">
            <label className="mb-1.5 block text-xs font-medium text-stone-500">Requesting org</label>
            {orgs.isLoading || orgs.isError ? (
              <QueryState isLoading={orgs.isLoading} isError={orgs.isError} error={orgs.error} loadingLabel="Finding the organisations" />
            ) : (
              <select
                value={effectiveOrgCode}
                onChange={(e) => setOrgCode(e.target.value)}
                disabled={lockedOrg != null}
                title={lockedOrg ? `Acting as ${lockedOrg}'s steward` : undefined}
                className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
              >
                {orgs.data?.map((org) => (
                  <option key={org.code} value={org.code}>{org.code}</option>
                ))}
              </select>
            )}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-stone-500">Material family</label>
            <select
              value={effectiveFamily}
              onChange={(e) => setFamily(e.target.value)}
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
            >
              {families.data?.map((f) => (
                <option key={f.family} value={f.family}>{f.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-1.5 block text-xs font-medium text-stone-500">Raw description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. HEX BOLT M10 X 120 A2-70 DIN 931"
              className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm focus:border-primary-300 focus:outline-none"
            />
          </div>
          <button
            type="button"
            disabled={!description.trim() || !effectiveOrgCode || !effectiveFamily || check.isPending}
            onClick={() =>
              check.mutate({ description, org_code: effectiveOrgCode, family: effectiveFamily })}
            className="rounded-lg bg-primary-500 px-5 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
          >
            {check.isPending ? 'Checking…' : 'Check'}
          </button>
        </div>
      </div>

      {check.isError && (
        <QueryState isLoading={false} isError error={check.error} />
      )}

      {check.data && <CheckOutcome result={check.data} description={description} orgCode={effectiveOrgCode} />}
    </div>
  )
}

function CheckOutcome({
  result,
  description,
  orgCode,
}: {
  result: CheckResult
  description: string
  orgCode: string
}) {
  if (result.safe_to_create) {
    return (
      <div className="rounded-2xl border border-brand-100 bg-brand-50/50 p-6 text-center">
        <p className="text-lg font-semibold text-brand-700">Safe to create</p>
        <p className="mt-1 text-sm text-brand-600">{result.message}</p>
        <p className="mt-1 text-xs text-brand-500">
          No existing canonical material matches "{description}" — {orgCode} can mint a new code.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl border border-rose-100 bg-rose-50/50 px-5 py-4">
        <p className="text-sm font-semibold text-rose-700">Not safe to create — a matching material already exists</p>
        <p className="mt-1 text-xs text-rose-600">{result.message}</p>
      </div>

      {result.candidates.map((candidate) => (
        <MatchComparison key={candidate.id} match={candidate} />
      ))}
    </div>
  )
}
