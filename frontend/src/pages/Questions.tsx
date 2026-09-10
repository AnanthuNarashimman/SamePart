import { useAnswer, useQuestions, useUnresolvable } from '../api/questions'
import { Pager, usePaged } from '../components/shared/Paginated'
import { Curve } from '../components/questions/Curve'
import { QuestionCard } from '../components/questions/QuestionCard'
import { QueryState } from '../components/shared/QueryState'

export function Questions() {
  const questions = useQuestions({ limit: 100 })
  const answer = useAnswer()
  const unresolvable = useUnresolvable()
  // Five at a time. A question card is tall and asks for a decision, so a page of them is a
  // sitting of work rather than a wall to scroll past.
  const paged = usePaged(questions.data?.items ?? [], 5)

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
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
              paged.slice.map((item) => (
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

            <Pager
              page={paged.page} pages={paged.pages} from={paged.from} to={paged.to}
              total={paged.total} unit="records to answer" onPage={paged.setPage}
              className="rounded-2xl border border-stone-100 bg-white px-5 py-3 shadow-sm"
            />
          </div>
        </>
      )}
    </div>
  )
}
