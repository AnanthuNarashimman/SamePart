import { useMigrationPreview } from '../../api/analytics'
import { QueryState } from '../shared/QueryState'

// What loading this back into a CPSE's master would actually do.
//
// The number the page is built around is zero. Every programme in this space asks a plant team
// to let software rewrite their material master, which is why plant teams say no and the
// programmes stall. This one adds columns beside a code and never touches the code itself, and
// that is worth stating as a figure somebody can check rather than a reassurance in a slide.
//
// It is on the import page deliberately: this is where a CPSE thinks about its own master, and
// the honest sequence is "here is what you gave us" then "here is exactly what goes back".

export function MigrationPreview({ orgCode }: { orgCode: string }) {
  const preview = useMigrationPreview(orgCode)

  if (preview.isLoading || preview.isError) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-stone-100 bg-white shadow-sm">
        <QueryState isLoading={preview.isLoading} isError={preview.isError} error={preview.error} />
      </div>
    )
  }

  const d = preview.data
  if (!d) return null

  const ACTION_LABEL: Record<string, string> = {
    cross_reference: 'Gain a national reference',
    review: 'Unchanged, still under review',
    close_recommended: 'Recommended for closure',
  }

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-stone-900">
        What this would change in {orgCode}&apos;s master
      </h3>
      <p className="mb-4 text-xs text-stone-400">
        A dry run. Nothing below has been written anywhere.
      </p>

      <div className="mb-4 grid grid-cols-3 gap-3">
        <Figure value={d.codes_in_master.toLocaleString('en-IN')} label="codes examined" />
        <Figure value={d.rows_added.toLocaleString('en-IN')} label="rows added" />
        {/* The whole argument, and the reason it is the loudest thing here. */}
        <Figure value="0" label="existing fields altered" emphasis />
      </div>

      <ul className="mb-4 flex flex-col gap-1.5">
        {Object.entries(d.by_action).map(([action, n]) => (
          <li key={action} className="flex items-baseline justify-between gap-3 text-xs">
            <span className="text-stone-600">{ACTION_LABEL[action] ?? action}</span>
            <span className="font-mono tabular-nums text-stone-900">
              {(n as number).toLocaleString('en-IN')}
            </span>
          </li>
        ))}
      </ul>

      <div className="grid gap-4 border-t border-stone-100 pt-3.5 sm:grid-cols-2">
        <Columns
          title="Columns written"
          tone="text-stone-700"
          items={d.columns_written as string[]}
        />
        <Columns
          title="Read, never written"
          tone="text-stone-400"
          items={d.columns_read_only as string[]}
        />
      </div>

      {d.notes?.length > 0 && (
        <p className="mt-3.5 border-t border-stone-100 pt-3 text-[11px] leading-relaxed text-stone-500">
          {d.notes[0]}
        </p>
      )}
    </div>
  )
}

function Figure({ value, label, emphasis }: { value: string; label: string; emphasis?: boolean }) {
  return (
    <div className={emphasis ? 'rounded-xl bg-stone-900 px-3 py-2.5' : 'px-1 py-2.5'}>
      <p
        className={`font-mono text-2xl leading-none tabular-nums ${
          emphasis ? 'text-white' : 'text-stone-900'
        }`}
      >
        {value}
      </p>
      <p className={`mt-1.5 text-[11px] ${emphasis ? 'text-stone-400' : 'text-stone-500'}`}>
        {label}
      </p>
    </div>
  )
}

function Columns({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div>
      <p className="mb-1.5 font-mono text-[10px] uppercase tracking-widest text-stone-400">
        {title}
      </p>
      <ul className={`flex flex-col gap-0.5 font-mono text-[11px] ${tone}`}>
        {items.map((c) => (
          <li key={c} className="truncate" title={c}>
            {c}
          </li>
        ))}
      </ul>
    </div>
  )
}
