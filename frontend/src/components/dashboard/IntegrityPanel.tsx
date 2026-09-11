import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/apiClient'
import { QueryState } from '../shared/QueryState'

// Whether the identifiers this system has issued are sound.
//
// It is on the dashboard rather than buried in a governance screen because the question it
// answers — has anything been altered, has any number been issued twice — is the one a CPSE
// asks before it agrees to anything, and an answer nobody can find is not an answer.
//
// Deliberately not a green tick with the word "secure". Each row names a property that could
// genuinely fail and says what was checked, because a panel that can only ever say yes is
// decoration.

interface Finding {
  check: string
  passed: boolean
  detail: string
  offenders: string[]
}

interface Report {
  identifiers_issued: number
  all_passed: boolean
  findings: Finding[]
}

export function IntegrityPanel() {
  const report = useQuery({
    queryKey: ['integrity'],
    queryFn: async () => (await apiClient.get<Report>('/governance/integrity')).data,
  })

  if (report.isLoading || report.isError) {
    return (
      <div className="flex h-44 items-center justify-center rounded-2xl border border-stone-100 bg-white shadow-sm">
        <QueryState isLoading={report.isLoading} isError={report.isError} error={report.error} loadingLabel="Walking the audit chain" />
      </div>
    )
  }

  const d = report.data
  if (!d) return null
  const failed = d.findings.filter((f) => !f.passed)

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-stone-900">Identifier integrity</h3>
        <span
          className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide ${
            d.all_passed ? 'bg-stone-900 text-white' : 'bg-rose-600 text-white'
          }`}
        >
          {d.all_passed ? `${d.findings.length}/${d.findings.length} CHECKS HOLD` : `${failed.length} FAILING`}
        </span>
      </div>
      <p className="mb-4 text-xs text-stone-400">
        {d.identifiers_issued.toLocaleString('en-IN')} national identifiers issued. Each check
        below is a property that could fail.
      </p>

      <ul className="flex flex-col divide-y divide-stone-100">
        {d.findings.map((f) => (
          <li key={f.check} className="flex gap-3 py-2.5">
            <span
              aria-hidden
              className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                f.passed ? 'bg-stone-300' : 'bg-rose-500'
              }`}
            />
            <span className="min-w-0">
              <span
                className={`block text-xs font-medium ${
                  f.passed ? 'text-stone-700' : 'text-rose-700'
                }`}
              >
                {f.check}
                <span className="sr-only">{f.passed ? ': passed' : ': failed'}</span>
              </span>
              <span className="mt-0.5 block text-[11px] leading-relaxed text-stone-500">
                {f.detail}
              </span>
              {f.offenders.length > 0 && (
                <span className="mt-1 block font-mono text-[10.5px] text-rose-600">
                  {f.offenders.slice(0, 3).join(' · ')}
                  {f.offenders.length > 3 && ` · +${f.offenders.length - 3} more`}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
