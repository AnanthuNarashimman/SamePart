import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

// Who is at the keyboard.
//
// The product's governance is two-tier: a CPSE's steward decides about that CPSE's own codes
// and answers questions only about its own records; a national approver is the only role that
// can say two organisations' codes are one material, which is the moment a national identifier
// exists. The backend has enforced that for some time. The frontend never told it who was
// asking, so every request arrived as the national approver and the rule never fired.
//
// This is a session, not a login. The demo key gets you in; this says who you are. Binding
// the two to real accounts is a deployment-phase item and is said so on the slide.

export type Actor =
  | { role: 'steward'; org: string }
  | { role: 'national_approver' }

export const NATIONAL: Actor = { role: 'national_approver' }

const STORAGE_KEY = 'meridian:actor'

/** The string that goes on the audit event. Mirrors `governance.actor_name` on the server. */
export function actorName(a: Actor): string {
  return a.role === 'steward' ? `${a.org}-steward` : 'national-approver'
}

export function actorRoleLabel(a: Actor): string {
  return a.role === 'steward' ? 'CPSE Data Steward' : 'National Codification Approver'
}

/** The fields every write request carries, so the server can rule on it and sign it. */
export function reviewerFields(a: Actor) {
  return {
    reviewer: actorName(a),
    reviewer_role: a.role,
    reviewer_org: a.role === 'steward' ? a.org : null,
  }
}

/** Query parameters that scope a read to what this actor may act on. */
export function actorParams(a: Actor) {
  return a.role === 'steward'
    ? { actor_role: a.role, actor_org: a.org }
    : { actor_role: a.role }
}

function load(): Actor {
  // A link can open the product already acting as someone — `?actor=BPCL` or
  // `?actor=national` — so a judge's link lands them in the right seat without a click.
  try {
    const fromUrl = new URLSearchParams(window.location.search).get('actor')
    if (fromUrl === 'national') return NATIONAL
    if (fromUrl && /^[A-Z]{2,6}$/.test(fromUrl)) return { role: 'steward', org: fromUrl }
  } catch {
    // no window, or a malformed query — fall through to the stored session
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Actor
      if (parsed.role === 'national_approver') return NATIONAL
      if (parsed.role === 'steward' && typeof parsed.org === 'string') return parsed
    }
  } catch {
    // no stored session, or storage unavailable — start as a steward once orgs load
  }
  return NATIONAL
}

interface ActorContextValue {
  actor: Actor
  setActor: (a: Actor) => void
}

const ActorContext = createContext<ActorContextValue | null>(null)

export function ActorProvider({ children }: { children: ReactNode }) {
  const [actor, setActorState] = useState<Actor>(load)
  const setActor = useCallback((a: Actor) => {
    setActorState(a)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(a))
    } catch {
      // per-viewer convenience only
    }
  }, [])
  const value = useMemo(() => ({ actor, setActor }), [actor, setActor])
  return <ActorContext.Provider value={value}>{children}</ActorContext.Provider>
}

export function useActor(): ActorContextValue {
  const ctx = useContext(ActorContext)
  if (!ctx) throw new Error('useActor must be used inside ActorProvider')
  return ctx
}
