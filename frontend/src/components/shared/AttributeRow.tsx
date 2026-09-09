import type { AttributeView } from '../../api/types'

const CRITICALITY_DOT: Record<string, string> = {
  identity: 'bg-violet-400',
  critical: 'bg-rose-400',
  major: 'bg-amber-400',
  minor: 'bg-stone-300',
}

export function AttributeRow({ a, b }: { a: AttributeView; b: AttributeView }) {
  const disagree = a.status === 'extracted' && b.status === 'extracted' && a.value !== b.value
  const eitherUnknown = a.status === 'unknown' || b.status === 'unknown'

  return (
    <div
      className={`grid grid-cols-[minmax(0,1fr)_11rem_11rem] items-start gap-3 rounded-lg px-2 py-2 text-sm ${
        disagree ? 'bg-rose-50/60' : eitherUnknown ? 'bg-amber-50/50' : ''
      }`}
    >
      <div className="flex items-center gap-2 pt-0.5 text-stone-500">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${CRITICALITY_DOT[a.criticality] ?? 'bg-stone-300'}`} />
        {a.label}
      </div>
      <ValueCell attr={a} />
      <ValueCell attr={b} />
    </div>
  )
}

function ValueCell({ attr }: { attr: AttributeView }) {
  if (attr.status === 'unknown') {
    return (
      <div>
        <p className="font-medium text-stone-400">unknown</p>
        <p className="text-xs text-stone-300">no evidence found</p>
      </div>
    )
  }

  return (
    <div>
      <p className="font-medium text-stone-900">
        {attr.value}
        {attr.unit ? ` ${attr.unit}` : ''}
      </p>
      {attr.evidence && <p className="truncate text-xs text-stone-400" title={attr.evidence}>&ldquo;{attr.evidence}&rdquo;</p>}
    </div>
  )
}
