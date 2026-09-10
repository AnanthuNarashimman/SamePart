// Target fields the pipeline understands — mirrors DEFAULT_COLUMN_MAP in
// backend/samepart/ingest/csv_loader.py. "source_code" and "description" are required by
// the loader; the rest are optional.
const TARGET_FIELDS = [
  'source_code',
  'description',
  'uom',
  'quantity',
  'unit_price',
  'manufacturer',
  'manufacturer_part_number',
] as const

interface ColumnMapperProps {
  columns: string[]
  mapping: Record<string, string>
  onChange: (sourceColumn: string, targetField: string) => void
}

// A per-source column-mapping config, not a hardcoded parser — every CPSE catalogue names
// its columns differently. See knowledge/10-frontend-plan.md #1.
export function ColumnMapper({ columns, mapping, onChange }: ColumnMapperProps) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <h3 className="mb-1 text-sm font-semibold text-stone-900">Map columns</h3>
      <p className="mb-4 text-xs text-stone-400">
        Match each column from this file to a field the pipeline understands. Unmapped
        columns are ignored.
      </p>
      <div className="flex flex-col divide-y divide-stone-100">
        {columns.map((col) => (
          <div key={col} className="flex items-center justify-between gap-4 py-2.5">
            <span className="rounded-md bg-stone-100 px-2 py-1 font-mono text-xs text-stone-600">{col}</span>
            <span className="text-stone-300">&rarr;</span>
            <select
              value={mapping[col] ?? ''}
              onChange={(e) => onChange(col, e.target.value)}
              className="w-56 rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-700 focus:border-primary-300 focus:outline-none"
            >
              <option value="">Ignore</option>
              {TARGET_FIELDS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  )
}
