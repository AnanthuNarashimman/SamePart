import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode,
} from 'react'

// A single page-wide "which CPSE am I looking at". Focusing an organisation in one panel
// fades the others everywhere at once, so "is this buyer consistently the expensive one"
// becomes one hover instead of a read of each panel in turn.
//
// The panels express the focus differently, because they encode the organisation differently:
// the price strips colour each dot by CPSE and so fade by colour, while the master comparison
// colours by tier and so fades whole columns. Same focus, same meaning, different marks.
//
// Hover previews the focus; click pins it, because a comparison you want to study should not
// evaporate the moment the pointer moves toward the thing you are comparing.

type OrgFocusValue = {
  /** The organisation currently emphasised, pinned or hovered. */
  focus: string | null
  /** True when the focus is held rather than following the pointer. */
  pinned: boolean
  hover: (org: string | null) => void
  toggle: (org: string) => void
  clear: () => void
}

const Ctx = createContext<OrgFocusValue>({
  focus: null,
  pinned: false,
  hover: () => {},
  toggle: () => {},
  clear: () => {},
})

export function OrgFocusProvider({ children }: { children: ReactNode }) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)

  const hover = useCallback((org: string | null) => setHovered(org), [])
  const toggle = useCallback((org: string) => setPinned((p) => (p === org ? null : org)), [])
  const clear = useCallback(() => {
    setPinned(null)
    setHovered(null)
  }, [])

  // A pinned focus is a mode, and a mode needs a way out that does not require finding the
  // control that set it.
  useEffect(() => {
    if (pinned === null) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setPinned(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [pinned])

  const value = useMemo<OrgFocusValue>(
    () => ({ focus: pinned ?? hovered, pinned: pinned !== null, hover, toggle, clear }),
    [pinned, hovered, hover, toggle, clear],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useOrgFocus = () => useContext(Ctx)

/** Opacity for a mark belonging to `org`. Unfocused marks fade rather than vanish: the shape
 *  of the whole distribution has to survive, otherwise focusing destroys the context that
 *  makes the focused mark mean anything. */
export function orgOpacity(org: string, focus: string | null): number {
  return focus === null || focus === org ? 1 : 0.16
}
