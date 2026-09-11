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
import { OrgFocusProvider } from '../components/insights/OrgFocus'
import { compact } from '../components/insights/tokens'
import { QueryState } from '../components/shared/QueryState'

function Placeholder({ q }: { q: { isLoading: boolean; isError: boolean; error: unknown } }) {
  return (
    <div className="flex h-72 items-center justify-center rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <QueryState isLoading={q.isLoading} isError={q.isError} error={q.error} loadingLabel="Measuring" />
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
    // One focus shared by every panel below: picking a CPSE in the price strips fades it in
    // the master comparison too, which is the whole reason the colours were made consistent.
    <OrgFocusProvider>
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
          value={cascade.data ? cascade.data.share_without_a_model * 100 : null}
          format={(n) => `${n.toFixed(1)}%`}
          label="decided without a model"
          sub={cascade.data
            ? `${cascade.data.decided_without_a_model.toLocaleString('en-IN')} of ${cascade.data.total_pairs.toLocaleString('en-IN')} pairs settled by rules alone`
            : 'measuring'}
        />
        <Hero
          delayMs={90}
          value={redistribution.data ? redistribution.data.total_avoided_spend : null}
          format={(n) => `₹${compact(n)}`}
          label="of purchasing avoidable"
          sub={redistribution.data
            ? `${redistribution.data.opportunities} materials one CPSE holds unused while another buys them`
            : 'measuring'}
        />
        <Hero
          tone="alert"
          delayMs={180}
          value={summary.data ? summary.data.dead_codes : null}
          format={(n) => Math.round(n).toLocaleString('en-IN')}
          label="dead material codes"
          sub={summary.data
            ? `${(summary.data.dead_code_rate * 100).toFixed(0)}% of every record, with no purchase order in four years`
            : 'measuring'}
        />
      </section>

      {/* Full width. It is one bar, so it wants width rather than height; pairing it beside
          a tall card is what left half a screen of white space. */}
      <section className="mb-5">
        {cascade.data ? <CascadeChart data={cascade.data} /> : <Placeholder q={cascade} />}
      </section>

      {/* items-start so a short card never stretches to match a tall neighbour. */}
      <section className="mb-5 grid grid-cols-1 items-start gap-5 xl:grid-cols-2">
        {spread.data ? <PriceSpreadChart data={spread.data} /> : <Placeholder q={spread} />}
        <div className="flex flex-col gap-5">
          {questions.data ? <StoppingCurve data={questions.data} /> : <Placeholder q={questions} />}
          {ageing.data ? <StockAgeingChart data={ageing.data} /> : <Placeholder q={ageing} />}
        </div>
      </section>

      <section>
        {summary.data ? <OrgComparison data={summary.data} /> : <Placeholder q={summary} />}
      </section>
    </div>
    </OrgFocusProvider>
  )
}
