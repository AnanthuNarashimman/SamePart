import { useState } from 'react'
import type { Question } from '../../api/types'

interface QuestionCardProps {
  item: Question
  onAnswer: (recordId: number, values: Record<string, string>) => void
  onUnresolvable: (recordId: number, keys: string[], reason: string) => void
  isSubmitting?: boolean
}

// One card per record, not one row per pair — the same record blocks many pairs and one
// answer clears all of them. See "the question view, which is where the volume is."
export function QuestionCard({ item, onAnswer, onUnresolvable, isSubmitting = false }: QuestionCardProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [reason, setReason] = useState('')

  const canSubmit = item.missing.every((m) => values[m.key])

  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-stone-900">{item.org_code} · {item.source_code}</p>
          <p className="text-xs text-stone-400">{item.raw_description}</p>
        </div>
        <span className="rounded-full bg-primary-50 px-2 py-1 text-[11px] font-medium text-primary-700">
          unblocks {item.pairs_blocked} pairs
        </span>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {item.missing.map((m) => (
          <div key={m.key}>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-xs font-medium text-stone-600">{m.label}</label>
              <span className="text-[11px] text-stone-400">blocks {m.pairs_blocked} pairs</span>
            </div>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {m.counterpart_values.map((cv) => (
                <button
                  key={cv.value}
                  type="button"
                  onClick={() => setValues((v) => ({ ...v, [m.key]: cv.value }))}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                    values[m.key] === cv.value
                      ? 'bg-primary-500 text-white'
                      : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                  }`}
                >
                  {cv.value} <span className="opacity-60">&times;{cv.seen_on}</span>
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="or type a value"
              value={values[m.key] ?? ''}
              onChange={(e) => setValues((v) => ({ ...v, [m.key]: e.target.value }))}
              className="w-full rounded-lg border border-stone-200 px-3 py-1.5 text-sm focus:border-primary-300 focus:outline-none"
            />
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-end gap-2">
        <input
          type="text"
          placeholder="reason it's unresolvable (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="mr-auto w-64 rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-primary-300 focus:outline-none"
        />
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onUnresolvable(item.record_id, item.missing.map((m) => m.key), reason || 'No source document available')}
          className="rounded-lg bg-stone-100 px-3 py-2 text-xs font-medium text-stone-600 hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Mark unresolvable
        </button>
        <button
          type="button"
          disabled={!canSubmit || isSubmitting}
          onClick={() => onAnswer(item.record_id, values)}
          className="rounded-lg bg-primary-500 px-4 py-2 text-xs font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
        >
          {isSubmitting ? 'Submitting…' : 'Submit answer'}
        </button>
      </div>
    </div>
  )
}
