// Charts that answer questions a judge or a data owner actually asks. Its own page: the
// relationship graph stays exactly as it is, at its own route.
import { useCascade, usePriceSpread, useRedistribution, useStockAgeing, useSummary } from '../api/analytics'
import { useQuestions } from '../api/questions'
import { CascadeChart } from '../components/insights/CascadeChart'
import { OrgComparison } from '../components/insights/OrgComparison'
import { PriceSpreadChart } from '../components/insights/PriceSpreadChart'
import { StockAgeingChart } from '../components/insights/StockAgeingChart'
import { StoppingCurve } from '../components/insights/StoppingCurve'
import { Hero } from '../components/insights/Hero'
import { compact } from '../components/insights/tokens'
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
  const redistribution = useRedistribution()

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Insights</h1>
        <p className="text-sm text-stone-400">
          How decisions were reached, what each CPSE paid, and where the stock is sitting
        </p>
      </header>

      {/* Three numbers, set large. A page of five charts of equal weight has no hierarchy and
          nothing for the eye to land on; this is what makes the rest read as evidence. */}
      <section className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Hero
          value={cascade.data ? `${(cascade.data.share_without_a_model * 100).toFixed(1)}%` : '—'}
          label="decided without a model"
          sub={cascade.data
            ? `${cascade.data.decided_without_a_model.toLocaleString('en-IN')} of ${cascade.data.total_pairs.toLocaleString('en-IN')} pairs settled by rules alone`
            : 'measuring'}
        />
        <Hero
          value={redistribution.data ? `₹${compact(redistribution.data.total_avoided_spend)}` : '—'}
          label="of purchasing avoidable"
          sub={redistribution.data
            ? `${redistribution.data.opportunities} materials one CPSE holds unused while another buys them`
            : 'measuring'}
        />
        <Hero
          tone="alert"
          value={summary.data ? summary.data.dead_codes.toLocaleString('en-IN') : '—'}
          label="dead material codes"
          sub={summary.data
            ? `${(summary.data.dead_code_rate * 100).toFixed(0)}% of every record, with no purchase order in four years`
            : 'measuring'}
        />
      </section>

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
