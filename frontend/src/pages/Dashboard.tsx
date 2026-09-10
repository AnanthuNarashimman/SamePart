import type { ReactNode } from 'react'
import { useAuditFlags, useRationalisation, useRedistribution, useSavings, useSummary } from '../api/analytics'
import { AuditFlagsPanel } from '../components/dashboard/AuditFlagsPanel'
import { IntegrityPanel } from '../components/dashboard/IntegrityPanel'
import { QueueBreakdown } from '../components/dashboard/QueueBreakdown'
import { RationalisationPanel } from '../components/dashboard/RationalisationPanel'
import { RedistributionPanel } from '../components/dashboard/RedistributionPanel'
import { SavingsPanel } from '../components/dashboard/SavingsPanel'
import { StatCard } from '../components/dashboard/StatCard'
import { QueryState } from '../components/shared/QueryState'
import { pct } from '../components/shared/formatters'

export function Dashboard() {
  const summary = useSummary()
  const savings = useSavings()
  const rationalisation = useRationalisation()
  const auditFlags = useAuditFlags()
  const redistribution = useRedistribution()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Dashboard</h1>
          <p className="text-sm text-stone-400">
            Operational summary across all connected CPSEs
          </p>
        </div>
        <img src="/logo.png" alt="Meridian" className="h-16 w-16 shrink-0 object-contain" />
      </header>

      {!summary.data ? (
        <QueryState isLoading={summary.isLoading} isError={summary.isError} error={summary.error} />
      ) : (
        <section className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard label="Records imported" value={summary.data.records.toLocaleString('en-IN')} hint="Across connected sources" />
          <StatCard label="Canonical materials" value={summary.data.canonical_materials.toLocaleString('en-IN')} />
          <StatCard label="Duplicates merged" value={summary.data.merged.toLocaleString('en-IN')} />
          <StatCard label="Conflicts caught" value={summary.data.conflicts_caught.toLocaleString('en-IN')} hint="Gate-overridden verdicts" />
          <StatCard
            label="Duplicate rate"
            value={pct(summary.data.duplicate_rate)}
            hint="Of imported records"
            accent="dark"
          />
        </section>
      )}

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {!savings.data ? (
            <Card><QueryState isLoading={savings.isLoading} isError={savings.isError} error={savings.error} /></Card>
          ) : (
            <SavingsPanel savings={savings.data} />
          )}
        </div>
        {!summary.data ? (
          <Card><QueryState isLoading={summary.isLoading} isError={summary.isError} error={summary.error} /></Card>
        ) : (
          <QueueBreakdown counts={summary.data.queue_by_group} />
        )}
      </section>

      {/* Full width, above the rest. This is the only finding in the product that is
          impossible without cross-organisation identity, so it does not sit in a corner. */}
      <section className="mt-5">
        {!redistribution.data ? (
          <Card>
            <QueryState
              isLoading={redistribution.isLoading}
              isError={redistribution.isError}
              error={redistribution.error}
            />
          </Card>
        ) : (
          <RedistributionPanel data={redistribution.data} />
        )}
      </section>

      <section className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {!rationalisation.data ? (
          <Card><QueryState isLoading={rationalisation.isLoading} isError={rationalisation.isError} error={rationalisation.error} /></Card>
        ) : (
          <RationalisationPanel data={rationalisation.data} />
        )}
        {!auditFlags.data ? (
          <Card><QueryState isLoading={auditFlags.isLoading} isError={auditFlags.isError} error={auditFlags.error} /></Card>
        ) : (
          <AuditFlagsPanel data={auditFlags.data} />
        )}
      </section>

      {/* The question a CPSE asks before agreeing to anything: has any number been issued
          twice, and has the record of who approved what been altered. An answer nobody can
          find is not an answer. */}
      <section className="mt-5">
        <IntegrityPanel />
      </section>
    </div>
  )
}

function Card({ children }: { children: ReactNode }) {
  return <div className="h-80 rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">{children}</div>
}
