import type { DecisionAction, MatchDetail } from '../../api/types'

interface DecisionBarProps {
  match: MatchDetail
  onDecide: (action: DecisionAction) => void
  onGoToQuestion: () => void
  isPending?: boolean
}

// POST /api/matches/{id}/decision refuses "approve" on insufficient_evidence with a 500 —
// the UI offers "answer the question" there instead of a doomed approve button. Reflects
// the record's real review_state rather than tracking a fake local "decided" flag, so a
// refresh or a decision made elsewhere shows correctly.
export function DecisionBar({ match, onDecide, onGoToQuestion, isPending = false }: DecisionBarProps) {
  const needsInput = match.verdict === 'insufficient_evidence'

  if (match.review_state !== 'queued') {
    return (
      <div className="flex items-center justify-between rounded-2xl border border-stone-100 bg-white px-5 py-4 shadow-sm">
        <p className="text-sm text-stone-500">
          Recorded as <span className="font-medium text-stone-900">{match.review_state.replace('_', ' ')}</span>.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-100 bg-white px-5 py-4 shadow-sm">
      <p className="min-w-0 flex-1 text-xs text-stone-400">
        {needsInput
          ? 'This pair cannot be approved yet — a critical attribute is unknown on at least one side.'
          : 'Review the comparison above, then record a decision.'}
      </p>
      <div className="flex shrink-0 gap-2">
        {needsInput ? (
          <button
            type="button"
            onClick={onGoToQuestion}
            className="whitespace-nowrap rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
          >
            Answer the question
          </button>
        ) : (
          <button
            type="button"
            disabled={isPending}
            onClick={() => onDecide('approve')}
            className="whitespace-nowrap rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Approve
          </button>
        )}
        <button
          type="button"
          disabled={isPending}
          onClick={() => onDecide('reject')}
          className="whitespace-nowrap rounded-lg bg-stone-100 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Reject
        </button>
        <button
          type="button"
          disabled={isPending}
          onClick={() => onDecide('request_info')}
          className="whitespace-nowrap rounded-lg bg-stone-100 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Request info
        </button>
      </div>
    </div>
  )
}
