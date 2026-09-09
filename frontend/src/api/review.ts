import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { DecisionRequest, DecisionResult, MatchDetail, QueuePage } from './types'

export function useQueue(params: { group?: string; cursor?: string; limit?: number } = {}) {
  return useQuery({
    queryKey: ['queue', params],
    queryFn: async () => (await apiClient.get<QueuePage>('/queue', { params })).data,
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
  return useMutation({
    mutationFn: async (req: DecisionRequest) =>
      (await apiClient.post<DecisionResult>(`/matches/${matchId}/decision`, req)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['match', matchId] })
    },
  })
}
