import { useEffect, useRef, useState } from 'react'

// Animation primitives shared by every panel, so the page has one timing language rather than
// six. Everything here collapses to its final state under prefers-reduced-motion: the charts
// are read at rest, and motion is only ever the way they arrive.

export function usePrefersReducedMotion(): boolean {
  const query = '(prefers-reduced-motion: reduce)'
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches,
  )
  useEffect(() => {
    const mq = window.matchMedia(query)
    const sync = () => setReduced(mq.matches)
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])
  return reduced
}

/** Fast at the start, gentle at the end. Numbers that decelerate read as settling on a value;
 *  linear ones read as a slot machine still spinning. */
const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

/** Counts from wherever it currently sits to `target`. Re-targeting mid-flight resumes from
 *  the displayed value instead of snapping back to zero, so a refetch never jolts. */
export function useCountUp(target: number | null, durationMs = 1100): number {
  const reduced = usePrefersReducedMotion()
  const [value, setValue] = useState(0)
  const displayed = useRef(0)

  useEffect(() => {
    if (target == null) return
    if (reduced) {
      displayed.current = target
      setValue(target)
      return
    }
    const origin = displayed.current
    const start = performance.now()
    let raf = requestAnimationFrame(function tick(now: number) {
      const t = Math.min((now - start) / durationMs, 1)
      const next = origin + (target - origin) * easeOutExpo(t)
      displayed.current = next
      setValue(next)
      if (t < 1) raf = requestAnimationFrame(tick)
    })
    return () => cancelAnimationFrame(raf)
  }, [target, durationMs, reduced])

  return target == null ? 0 : value
}

/** Flips true one frame after mount, or after `delayMs` for staggering. Panels transition
 *  from a collapsed state to this one, which is what makes bars grow rather than appear. */
export function useReveal(delayMs = 0): boolean {
  const reduced = usePrefersReducedMotion()
  const [shown, setShown] = useState(false)

  useEffect(() => {
    if (reduced) {
      setShown(true)
      return
    }
    // Two frames: one for the browser to commit the collapsed state, one to transition off it.
    let timer = 0
    const raf = requestAnimationFrame(() => {
      timer = window.setTimeout(() => setShown(true), delayMs)
    })
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(timer)
    }
  }, [delayMs, reduced])

  return shown
}

/** Recharts animation settings, in one place so all five panels arrive on the same clock. */
export function chartMotion(reduced: boolean, beginMs = 0) {
  return {
    isAnimationActive: !reduced,
    animationBegin: beginMs,
    animationDuration: 900,
    animationEasing: 'ease-out' as const,
  }
}
