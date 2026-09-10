// Charts that answer questions a judge or a data owner actually asks. Its own page: the
// relationship graph stays exactly as it is, at its own route.
import { useCascade, usePriceSpread, useStockAgeing, useSummary } from '../api/analytics'
import { useQuestions } from '../api/questions'
import { CascadeChart } from '../components/insights/CascadeChart'
import { OrgComparison } from '../components/insights/OrgComparison'
import { PriceSpreadChart } from '../components/insights/PriceSpreadChart'
import { StockAgeingChart } from '../components/insights/StockAgeingChart'
import { StoppingCurve } from '../components/insights/StoppingCurve'
import { QueryState } from '../components/shared/QueryState'

function Placeholder({ q }: { q: { isLoading: boolean; isError: boolean; error: unknown } }) {
  return (
    <div className="flex h-72 items-center justify-center rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <QueryState isLoading={q.isLoading} isError={q.isError} error={q.error} />
    </div>
  )
}

export function Insights() {
  const cascade = useCascade()
  const spread = usePriceSpread()
  const ageing = useStockAgeing()
  const summary = useSummary()
  const questions = useQuestions({ limit: 1 })

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Insights</h1>
        <p className="text-sm text-stone-400">
          How decisions were reached, what each CPSE paid, and where the stock is sitting
        </p>
      </header>

      {/* The two that carry the pitch, first and side by side. */}
      <section className="mb-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
        {cascade.data ? <CascadeChart data={cascade.data} /> : <Placeholder q={cascade} />}
        {spread.data ? <PriceSpreadChart data={spread.data} /> : <Placeholder q={spread} />}
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {questions.data ? <StoppingCurve data={questions.data} /> : <Placeholder q={questions} />}
        {summary.data ? <OrgComparison data={summary.data} /> : <Placeholder q={summary} />}
        {ageing.data ? <StockAgeingChart data={ageing.data} /> : <Placeholder q={ageing} />}
      </section>
    </div>
  )
}
