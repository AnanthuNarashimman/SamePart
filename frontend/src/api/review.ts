import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { actorParams, reviewerFields, useActor } from '../lib/actor'
import { apiClient } from '../lib/apiClient'
import type { DecisionRequest, DecisionResult, MatchDetail, QueuePage } from './types'

export function useQueue(params: { group?: string; cursor?: string; limit?: number } = {}) {
  // Scoped to who is asking: a steward gets their own organisation's pairs, the national
  // approver gets everything. The actor is part of the key so switching refetches.
  const { actor } = useActor()
  const scoped = { ...params, ...actorParams(actor) }
  return useQuery({
    queryKey: ['queue', scoped],
    queryFn: async () => (await apiClient.get<QueuePage>('/queue', { params: scoped })).data,
    // Turning a page keeps the current one on screen until the next arrives, rather than
    // emptying the list and re-drawing it.
    placeholderData: keepPreviousData,
  })
}

export function useMatch(matchId: number | null) {
  return useQuery({
    queryKey: ['match', matchId],
    queryFn: async () => (await apiClient.get<MatchDetail>(`/matches/${matchId}`)).data,
    enabled: matchId != null,
  })
}

export function useDecision(matchId: number) {
  const queryClient = useQueryClient()
  const { actor } = useActor()
  return useMutation({
    // Signed by whoever is acting. The server rules on the role and writes the name to
    // the audit event; the frontend never decides what it is allowed to do.
    mutationFn: async (req: DecisionRequest) =>
      (await apiClient.post<DecisionResult>(`/matches/${matchId}/decision`,
        { ...reviewerFields(actor), ...req })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['match', matchId] })
    },
  })
}
