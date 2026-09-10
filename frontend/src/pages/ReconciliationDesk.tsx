import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDecision, useMatch, useQueue } from '../api/review'
import type { DecisionAction } from '../api/types'
import { QueueList } from '../components/desk/QueueList'
import { SurvivorshipPanel } from '../components/desk/SurvivorshipPanel'
import { DecisionBar } from '../components/desk/DecisionBar'
import { MatchComparison } from '../components/shared/MatchComparison'
import { QueryState } from '../components/shared/QueryState'

export function ReconciliationDesk() {
  const navigate = useNavigate()
  const queue = useQueue({ limit: 200 })
  const [selectedId, setSelectedId] = useState<number | null>(null)

  useEffect(() => {
    if (selectedId != null || !queue.data) return
    const preferred = queue.data.items.find((i) => i.verdict === 'insufficient_evidence') ?? queue.data.items[0]
    if (preferred) setSelectedId(preferred.id)
  }, [queue.data, selectedId])

  const match = useMatch(selectedId)
  const decision = useDecision(selectedId ?? -1)

  const handleDecide = (action: DecisionAction) => {
    decision.mutate({ action })
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-stone-50 p-8">
      <header className="mb-6 shrink-0">
        <h1 className="text-xl font-semibold text-stone-900">Reconciliation desk</h1>
        <p className="text-sm text-stone-400">
          {queue.data ? `${queue.data.items.length} pending pairs` : 'Loading pending pairs'} · grouped by reviewer
          priority, not alphabetically
        </p>
      </header>

      {queue.data && (
        <section className="mb-6 grid shrink-0 grid-cols-2 gap-3 sm:grid-cols-4">
          <MiniStat label="Needs input" value={queue.data.counts.needs_input} tone="text-rose-600" />
          <MiniStat label="Possible alternatives" value={queue.data.counts.possible_alternative} tone="text-amber-600" />
          <MiniStat label="Confirmed matches" value={queue.data.counts.same_material} tone="text-emerald-600" />
          <MiniStat label="Confirmed different" value={queue.data.counts.different} tone="text-stone-500" />
        </section>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-5 lg:flex-row">
        <div className="relative min-h-0 w-full shrink-0 lg:w-[22rem]">
          <div className="scroll-clean h-full overflow-y-auto pb-6 pr-2">
            {!queue.data ? (
              <QueryState isLoading={queue.isLoading} isError={queue.isError} error={queue.error} loadingLabel="Loading queue…" />
            ) : queue.data.items.length === 0 ? (
              <div className="flex h-64 items-center justify-center rounded-2xl border border-dashed border-stone-200 text-sm text-stone-400">
                Queue is empty
              </div>
            ) : (
              <QueueList items={queue.data.items} selectedId={selectedId} onSelect={setSelectedId} />
            )}
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-stone-50 to-transparent" />
        </div>

        <div className="scroll-clean flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto pr-2">
          {selectedId == null ? (
            <div className="flex h-64 items-center justify-center rounded-2xl border border-dashed border-stone-200 text-sm text-stone-400">
              Select a pair from the queue
            </div>
          ) : !match.data ? (
            <QueryState isLoading={match.isLoading} isError={match.isError} error={match.error} loadingLabel="Loading comparison…" />
          ) : (
            <>
              <MatchComparison match={match.data} />
              <SurvivorshipPanel match={match.data} />
              <DecisionBar
                match={match.data}
                onDecide={handleDecide}
                onGoToQuestion={() => navigate('/questions')}
                isPending={decision.isPending}
              />
              {decision.isError && (
                <p className="text-xs text-rose-500">
                  Decision failed: {decision.error instanceof Error ? decision.error.message : 'unknown error'}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs text-stone-400">{label}</p>
      <p className={`text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  )
}
