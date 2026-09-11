import type { ReactNode } from 'react'
import { useAuth } from './auth'

// Who is at the keyboard, as the server knows it.
//
// The seat is the signed-in account: the four CPSE stewards and the national approver. The
// server takes the role from the token it signed, so nothing here is trusted for permissions;
// it exists so screens can show the right queue, lock the right controls and name the seat.

export type Actor =
  | { role: 'steward'; org: string }
  | { role: 'national_approver' }

export const NATIONAL: Actor = { role: 'national_approver' }

export function actorRoleLabel(a: Actor): string {
  return a.role === 'steward' ? 'CPSE Data Steward' : 'National Codification Approver'
}

/** Query parameters that scope a read; the server applies the same scope from the token
 *  regardless, these only keep the query key honest so switching seats refetches. */
export function actorParams(a: Actor) {
  return a.role === 'steward'
    ? { actor_role: a.role, actor_org: a.org }
    : { actor_role: a.role }
}

/** Kept for call sites that spread it into a body; the server overwrites these fields. */
export function reviewerFields(a: Actor) {
  return {
    reviewer: a.role === 'steward' ? `${a.org}-steward` : 'national-approver',
    reviewer_role: a.role,
    reviewer_org: a.role === 'steward' ? a.org : null,
  }
}

export function ActorProvider({ children }: { children: ReactNode }) {
  return <>{children}</>
}

export function useActor(): { actor: Actor } {
  const { session } = useAuth()
  if (!session) return { actor: NATIONAL }
  return {
    actor: session.role === 'steward' && session.org
      ? { role: 'steward', org: session.org }
      : NATIONAL,
  }
}
