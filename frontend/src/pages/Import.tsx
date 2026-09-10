import { useState } from 'react'
import { useFamilies, useOrgs, useStartImport } from '../api/catalogue'
import { MigrationPreview } from '../components/import/MigrationPreview'
import { ColumnMapper } from '../components/import/ColumnMapper'
import { ImportHistory } from '../components/import/ImportHistory'
import { QueryState } from '../components/shared/QueryState'

// Reads just the header row of the real file the user picked — no synthetic column list.
function readHeaderRow(file: File): Promise<string[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result ?? '')
      const firstLine = text.split(/\r?\n/, 1)[0] ?? ''
      resolve(firstLine.split(',').map((h) => h.trim().replace(/^"|"$/g, '')).filter(Boolean))
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file.slice(0, 8192))
  })
}

export function Import() {
  const orgs = useOrgs()
  const startImport = useStartImport()
  const families = useFamilies()
  const [family, setFamily] = useState('')
  // Whatever the dictionary loaded first, until the reader chooses. Never a literal:
  // this form used to send no family at all and the API defaulted it to 'hex_bolt', so
  // a gasket catalogue imported through the UI landed as bolts, matched nothing, and
  // reported success.
  const effectiveFamily = family || families.data?.[0]?.family || ''

  const [orgCode, setOrgCode] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [columns, setColumns] = useState<string[]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [importIds, setImportIds] = useState<string[]>([])

  const effectiveOrgCode = orgCode ?? orgs.data?.[0]?.code ?? ''

  const handleFile = async (f: File | null) => {
    setFile(f)
    setMapping({})
    if (!f) {
      setColumns([])
      return
    }
    try {
      setColumns(await readHeaderRow(f))
    } catch {
      setColumns([])
    }
  }

  const handleStartImport = () => {
    if (!file || !effectiveOrgCode) return
    // ColumnMapper maps source column -> target field; the API wants target field -> source column.
    const columnMap = Object.fromEntries(
      Object.entries(mapping).filter(([, field]) => field).map(([col, field]) => [field, col]),
    )
    startImport.mutate(
      { file, orgCode: effectiveOrgCode, family: effectiveFamily, columnMap },
      { onSuccess: (status) => setImportIds((ids) => [status.import_id, ...ids]) },
    )
  }

  return (
    <div className="flex-1 overflow-y-auto app-canvas p-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-stone-900">Import</h1>
        <p className="text-sm text-stone-400">
          Bring in a catalogue or purchase-order file, one CPSE at a time
        </p>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-5">
          <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-stone-900">1. Choose source and file</h3>
            {orgs.isLoading || orgs.isError ? (
              <QueryState isLoading={orgs.isLoading} isError={orgs.isError} error={orgs.error} />
            ) : (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <select
                  value={effectiveOrgCode}
                  onChange={(e) => setOrgCode(e.target.value)}
                  className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
                >
                  {orgs.data?.map((org) => (
                    <option key={org.code} value={org.code}>{org.name} ({org.code})</option>
                  ))}
                </select>

                <select
                  value={effectiveFamily}
                  onChange={(e) => setFamily(e.target.value)}
                  aria-label="Material family"
                  className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-primary-300 focus:outline-none"
                >
                  {families.data?.map((f) => (
                    <option key={f.family} value={f.family}>{f.label}</option>
                  ))}
                </select>

                <label className="flex-1 cursor-pointer rounded-lg border border-dashed border-stone-300 px-4 py-2 text-center text-sm text-stone-500 hover:border-primary-300 hover:text-primary-600">
                  {file?.name ?? 'Choose CSV file'}
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
            )}
            <p className="mt-2 text-xs text-stone-400">
              Column names are detected from the file's header row and mapped below — no
              hardcoded per-source parser.
            </p>
          </div>

          {columns.length > 0 && (
            <ColumnMapper
              columns={columns}
              mapping={mapping}
              onChange={(col, field) => setMapping((m) => ({ ...m, [col]: field }))}
            />
          )}

          {columns.length > 0 && (
            <div className="flex items-center justify-between rounded-2xl border border-stone-100 bg-white px-5 py-4 shadow-sm">
              <p className="text-xs text-stone-400">
                {Object.values(mapping).filter(Boolean).length} of {columns.length} columns mapped
              </p>
              <button
                type="button"
                disabled={startImport.isPending}
                onClick={handleStartImport}
                className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
              >
                {startImport.isPending ? 'Starting…' : 'Start import'}
              </button>
            </div>
          )}

          {startImport.isSuccess && (
            <div className="rounded-2xl bg-brand-50 px-5 py-4 text-sm text-brand-700">
              {file?.name} queued for {effectiveOrgCode}. Regex/LLM attribute extraction runs
              next, then matching against the canonical set — check the panel on the right for
              live status.
            </div>
          )}
          {startImport.isError && (
            <div className="rounded-2xl bg-rose-50 px-5 py-4 text-sm text-rose-700">
              Import failed: {startImport.error instanceof Error ? startImport.error.message : 'unknown error'}
            </div>
          )}

          {/* The other half of the exchange. This page has always shown what a CPSE gives us;
              it never showed what goes back, which is the part they actually have to approve. */}
          {effectiveOrgCode && <MigrationPreview orgCode={effectiveOrgCode} />}
        </div>

        <ImportHistory importIds={importIds} />
      </div>
    </div>
  )
}
