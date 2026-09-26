import { useRef, useState } from 'react'
import { fetchFamilyYaml, useFamilies, useLoadFamily, useRemoveFamily } from '../../api/catalogue'
import { useActor } from '../../lib/actor'

// The families the dictionary carries, and the way a new one gets in.
//
// "Families are data, not code" was true of the pipeline and false of the product: the only
// way to add one was curl with a token, and it vanished on the next restart. This is the
// screen for it. Everyone sees what is loaded; the national approver can paste or pick a
// YAML file, is told exactly what is wrong with it if anything, and the addition lands in
// the audit trail like any other decision. Records already imported are not re-read; the
// family applies to imports made from now on.

export function FamilyManager() {
  const families = useFamilies()
  const load = useLoadFamily()
  const remove = useRemoveFamily()
  const { actor } = useActor()
  // A removal the server refused because records exist: name and count, awaiting a purge.
  const [pendingPurge, setPendingPurge] = useState<{ name: string; records: number } | null>(null)
  const [removeNote, setRemoveNote] = useState<string | null>(null)

  const askRemove = (name: string, purge = false) => {
    setRemoveNote(null)
    remove.mutate({ name, purge }, {
      onSuccess: (r) => {
        setPendingPurge(null)
        setRemoveNote(r.records_removed
          ? `Removed ${r.family} and its ${r.records_removed} records.`
          : `Removed ${r.family}.`)
      },
      onError: (err) => {
        const detail = (err as { response?: { status?: number; data?: { detail?: unknown } } })?.response?.data?.detail
        if (typeof detail === 'object' && detail && 'records' in detail) {
          const d = detail as { message: string; records: number; decided: number }
          if (d.decided > 0) { setPendingPurge(null); setRemoveNote(d.message) }
          else setPendingPurge({ name, records: d.records })
          return
        }
        setPendingPurge(null)
        setRemoveNote(typeof detail === 'string' ? detail : 'Could not remove the family.')
      },
    })
  }
  const mayAdd = actor.role === 'national_approver'

  const [open, setOpen] = useState(false)
  const [yaml, setYaml] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  const [replace, setReplace] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const pickFile = async (f: File | null) => {
    if (!f) return
    setFileName(f.name)
    setYaml(await f.text())
  }

  const startFrom = async (name: string) => {
    try {
      setYaml(await fetchFamilyYaml(name))
      setFileName(`${name}.yaml (copy)`)
      setOpen(true)
    } catch {
      /* the list already shows the family; nothing to recover here */
    }
  }

  const submit = () => {
    if (!yaml.trim()) return
    load.mutate({ yaml, replace }, {
      onSuccess: () => { setYaml(''); setFileName(null); setReplace(false) },
    })
  }

  const clash = load.isError && (load.error as { response?: { status?: number } })?.response?.status === 409
  const errorText = load.isError
    ? ((load.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ?? (load.error instanceof Error ? load.error.message : 'unknown error'))
    : null

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-stone-900">Families in the catalogue</h3>
          <p className="text-xs text-stone-400">
            Each family is one YAML file: attributes, units, gates, blocking. No code changes.
          </p>
        </div>
        {mayAdd && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-700 hover:border-primary-300 hover:text-primary-600"
          >
            {open ? 'Close' : 'Add a family'}
          </button>
        )}
      </div>

      <ul className="mt-3 flex flex-wrap gap-2">
        {families.data?.map((f) => (
          <li
            key={f.family}
            title={f.classification_path ?? undefined}
            className="flex items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs"
          >
            <span className="font-medium text-stone-800">{f.label}</span>
            <span className="font-mono text-[10px] text-stone-400">
              {f.attribute_count} attr · {f.gate_count} gates
            </span>
            {f.added && (
              <span className="rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold text-brand-900">
                added
              </span>
            )}
            {mayAdd && f.added && (
              <button
                type="button"
                onClick={() => askRemove(f.family)}
                disabled={remove.isPending}
                className="text-[10px] text-rose-500 underline-offset-2 hover:underline disabled:text-stone-300"
                title="Remove this family (only families added at runtime can be removed here)"
              >
                remove
              </button>
            )}
            {mayAdd && (
              <button
                type="button"
                onClick={() => startFrom(f.family)}
                className="text-[10px] text-stone-400 underline-offset-2 hover:text-primary-600 hover:underline"
                title={`Open ${f.family}.yaml as a starting point`}
              >
                copy
              </button>
            )}
          </li>
        ))}
      </ul>

      {pendingPurge && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-khaki-50 px-4 py-3 text-sm text-khaki-800">
          <span>
            <b>{pendingPurge.records}</b> records were imported under <b>{pendingPurge.name}</b>.
            Remove the family together with those records and everything matched from them?
          </span>
          <span className="flex gap-2">
            <button type="button" onClick={() => setPendingPurge(null)} className="rounded-lg border border-khaki-200 px-3 py-1.5 text-xs">Keep</button>
            <button
              type="button"
              onClick={() => askRemove(pendingPurge.name, true)}
              className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700"
            >
              Remove family and {pendingPurge.records} records
            </button>
          </span>
        </div>
      )}
      {removeNote && (
        <p className="mt-3 rounded-lg bg-stone-50 px-4 py-2 text-xs text-stone-600">{removeNote}</p>
      )}

      {mayAdd && open && (
        <div className="mt-4 border-t border-stone-100 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer rounded-lg border border-dashed border-stone-300 px-4 py-2 text-sm text-stone-500 hover:border-primary-300 hover:text-primary-600">
              {fileName ?? 'Choose a family YAML'}
              <input
                ref={fileInput}
                type="file"
                accept=".yaml,.yml"
                className="hidden"
                onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <span className="text-xs text-stone-400">or paste it below</span>
            <label className="ml-auto flex items-center gap-2 text-xs text-stone-500">
              <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
              replace if the name exists
            </label>
          </div>

          <textarea
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            spellCheck={false}
            rows={10}
            placeholder={'family: flange_weld_neck\nlabel: Flange, weld neck\nnaming: …\nattributes: …\ngates: …'}
            className="mt-3 w-full rounded-lg border border-stone-200 bg-stone-50 p-3 font-mono text-xs text-stone-800 focus:border-primary-300 focus:outline-none"
          />

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-stone-400">
              Validated against the unit registry before it loads. Applies to imports from now on;
              nothing already imported is re-read.
            </p>
            <button
              type="button"
              disabled={load.isPending || !yaml.trim()}
              onClick={submit}
              className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
            >
              {load.isPending ? 'Loading…' : replace ? 'Replace family' : 'Add family'}
            </button>
          </div>

          {load.isSuccess && (
            <div className="mt-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-700">
              {load.data.replaced ? 'Replaced' : 'Added'} <b>{load.data.label}</b> ·{' '}
              {load.data.attribute_count} attributes, {load.data.gate_count} gates. It is in the
              family list above and recorded in the audit trail.
            </div>
          )}
          {errorText && (
            <div className="mt-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {clash ? 'A family with that name is already loaded. ' : 'Not loaded: '}
              {errorText}
              {clash && ' Tick "replace" to overwrite it, or rename this one.'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
