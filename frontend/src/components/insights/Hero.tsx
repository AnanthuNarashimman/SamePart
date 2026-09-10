import type { ReactNode } from 'react'
import { INK } from './tokens'
import { useCountUp, useReveal } from './motion'

// Impact comes from hierarchy, not from more chart. One number at the top of the page, set
// large enough to be read from across a room, with the chart beneath it as the evidence.
//
// The number counts up rather than appearing. That is not decoration: it takes a figure the
// eye would skip over and makes it the thing that moves on an otherwise still page, which is
// exactly where a first-time reader should be looking. It takes a raw number and a formatter
// instead of a finished string, because only the raw number can be interpolated.
export function Hero({
  value,
  format,
  label,
  sub,
  tone = 'default',
  delayMs = 0,
}: {
  value: number | null
  format: (n: number) => string
  label: string
  sub?: ReactNode
  tone?: 'default' | 'alert'
  delayMs?: number
}) {
  const shown = useReveal(delayMs)
  const animated = useCountUp(value, 1100)

  return (
    <div
      className="rounded-2xl border border-stone-100 bg-white px-6 py-5 shadow-sm transition-all
                 duration-500 ease-out motion-reduce:transition-none"
      style={{ opacity: shown ? 1 : 0, transform: shown ? 'none' : 'translateY(8px)' }}
    >
      <p
        className="font-mono text-[2.75rem] leading-none tracking-tight tabular-nums"
        style={{ color: tone === 'alert' ? '#d03b3b' : INK.strong }}
      >
        {value === null ? '—' : format(animated)}
      </p>
      <p className="mt-2 text-sm font-medium text-stone-800">{label}</p>
      {sub && <p className="mt-1 text-xs leading-relaxed text-stone-400">{sub}</p>}
    </div>
  )
}
