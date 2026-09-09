import { useAnswer, useQuestions, useUnresolvable } from '../api/questions'
import { Curve } from '../components/questions/Curve'
import { QuestionCard } from '../components/questions/QuestionCard'
import { QueryState } from '../components/shared/QueryState'

export function Questions() {
  const questions = useQuestions({ limit: 100 })
  const answer = useAnswer()
  const unresolvable = useUnresolvable()

  return (
    <div className="flex-1 overflow-y-auto bg-stone-50 p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Answer the questions</h1>
        <p className="text-sm text-stone-400">
          {questions.data
            ? (
              <>
                {questions.data.pairs_deferred} pairs deferred · {questions.data.questions} distinct blanks ·{' '}
                <span className="font-medium text-stone-600">{questions.data.records} records to open</span>
              </>
            )
            : 'Loading…'}
        </p>
      </header>

      {!questions.data ? (
        <QueryState isLoading={questions.isLoading} isError={questions.isError} error={questions.error} loadingLabel="Loading questions…" />
      ) : (
        <>
          {questions.data.curve.length > 0 && (
            <div className="mb-6">
              <Curve curve={questions.data.curve} />
            </div>
          )}

          <div className="flex flex-col gap-4">
            {questions.data.items.length === 0 ? (
              <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-stone-200 text-sm text-stone-400">
                No open questions
              </div>
            ) : (
              questions.data.items.map((item) => (
                <QuestionCard
                  key={item.record_id}
                  item={item}
                  isSubmitting={
                    (answer.isPending && answer.variables?.recordId === item.record_id) ||
                    (unresolvable.isPending && unresolvable.variables?.recordId === item.record_id)
                  }
                  onAnswer={(recordId, values) => answer.mutate({ recordId, req: { values } })}
                  onUnresolvable={(recordId, keys, reason) =>
                    unresolvable.mutate({ recordId, req: { keys, reason } })
                  }
                />
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}
