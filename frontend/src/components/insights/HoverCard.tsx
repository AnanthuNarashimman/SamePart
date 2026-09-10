import { useCallback, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

// The hand-built panels — the cascade bar and the price strips — are plain elements, so they
// have no Recharts tooltip to inherit. This gives them the same hover layer.
//
// It replaces the browser's native title attribute, which took about a second to appear, could
// not be styled, and could not show more than one line. A chart whose only readout is a native
// tooltip is effectively not interactive.

export type HoverAnchor = { x: number; y: number; node: ReactNode } | null

export function useHoverCard() {
  const [anchor, setAnchor] = useState<HoverAnchor>(null)

  const show = useCallback((event: { clientX: number; clientY: number }, node: ReactNode) => {
    setAnchor({ x: event.clientX, y: event.clientY, node })
  }, [])
  const hide = useCallback(() => setAnchor(null), [])

  return { anchor, show, hide }
}

export function HoverCard({ anchor }: { anchor: HoverAnchor }) {
  if (!anchor || typeof document === 'undefined') return null

  // Flip to the other side of the cursor near the viewport edge, so the card never gets
  // clipped by the window and never covers the mark it is describing.
  const flipX = anchor.x > window.innerWidth - 260
  const flipY = anchor.y > window.innerHeight - 120

  return createPortal(
    <div
      role="tooltip"
      className="pointer-events-none fixed z-50 max-w-[240px] rounded-lg border border-stone-200
                 bg-white px-2.5 py-2 text-xs leading-relaxed text-stone-700 shadow-lg
                 shadow-stone-900/10"
      style={{
        left: anchor.x + (flipX ? -14 : 14),
        top: anchor.y + (flipY ? -14 : 14),
        transform: `translate(${flipX ? '-100%' : '0'}, ${flipY ? '-100%' : '0'})`,
      }}
    >
      {anchor.node}
    </div>,
    document.body,
  )
}
