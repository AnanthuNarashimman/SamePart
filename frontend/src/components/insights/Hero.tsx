import type { ReactNode } from 'react'
import { INK } from './tokens'

// Impact comes from hierarchy, not from more chart. One number at the top of the page, set
// large enough to be read from across a room, with the chart beneath it as the evidence.
export function Hero({
  value,
  label,
  sub,
  tone = 'default',
}: {
  value: string
  label: string
  sub?: ReactNode
  tone?: 'default' | 'alert'
}) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-white px-6 py-5 shadow-sm">
      <p
        className="font-mono text-[2.75rem] leading-none tracking-tight"
        style={{ color: tone === 'alert' ? '#d03b3b' : INK.strong }}
      >
        {value}
      </p>
      <p className="mt-2 text-sm font-medium text-stone-800">{label}</p>
      {sub && <p className="mt-1 text-xs leading-relaxed text-stone-400">{sub}</p>}
    </div>
  )
}
