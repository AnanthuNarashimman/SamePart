import { useImportStatus } from '../../api/catalogue'

const STATUS_TONE: Record<string, string> = {
  pending: 'bg-stone-100 text-stone-500',
  running: 'bg-khaki-50 text-khaki-700',
  done: 'bg-brand-50 text-brand-700',
  complete: 'bg-brand-50 text-brand-700',
  failed: 'bg-rose-50 text-rose-700',
}

// There is no GET /api/imports (list) endpoint — only GET /api/imports/{id}. History here
// is therefore the imports started in this browser session, each polled live for status.
export function ImportHistory({ importIds }: { importIds: string[] }) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white shadow-sm">
      <div className="border-b border-stone-100 px-5 py-4">
        <h3 className="text-sm font-semibold text-stone-900">This session's imports</h3>
        <p className="text-xs text-stone-400">Live status, polled from the API</p>
      </div>
      {importIds.length === 0 ? (
        <p className="px-5 py-6 text-center text-sm text-stone-400">No imports started yet</p>
      ) : (
        <ul className="flex flex-col divide-y divide-stone-100">
          {importIds.map((id) => (
            <ImportRow key={id} importId={id} />
          ))}
        </ul>
      )}
    </div>
  )
}

function ImportRow({ importId }: { importId: string }) {
  const { data, isLoading, isError } = useImportStatus(importId)

  if (isLoading) {
    return <li className="px-5 py-3 text-xs text-stone-400">{importId} · loading…</li>
  }
  if (isError || !data) {
    return <li className="px-5 py-3 text-xs text-rose-500">{importId} · status unavailable</li>
  }

  return (
    <li className="flex items-center justify-between gap-4 px-5 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-stone-800">{data.import_id}</p>
        <p className="text-xs text-stone-400">{data.org_code}</p>
        {data.errors.length > 0 && (
          <p className="mt-0.5 truncate text-xs text-rose-500" title={data.errors.join('; ')}>
            {data.errors.length} error{data.errors.length > 1 ? 's' : ''}
          </p>
        )}
      </div>
      <div className="shrink-0 text-right">
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${STATUS_TONE[data.status] ?? 'bg-stone-100 text-stone-500'}`}>
          {data.status}
        </span>
        <p className="mt-1 text-xs text-stone-400">
          {data.rows_ingested}/{data.rows_read} rows · {data.attributes_extracted} attrs
        </p>
      </div>
    </li>
  )
}
