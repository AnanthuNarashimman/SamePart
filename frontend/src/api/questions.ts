import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reviewerFields, useActor } from '../lib/actor'
import { apiClient } from '../lib/apiClient'
import type { AnswerRequest, AnswerResult, QuestionPage, UnresolvableRequest } from './types'

export function useQuestions(params: { cursor?: string; limit?: number } = {}) {
  // A steward is asked only about their own records; nobody else knows what they meant.
  const { actor } = useActor()
  const scoped = actor.role === 'steward' ? { ...params, actor_org: actor.org } : params
  return useQuery({
    queryKey: ['questions', scoped],
    queryFn: async () => (await apiClient.get<QuestionPage>('/questions', { params: scoped })).data,
    // Turning a page keeps the current one on screen until the next arrives, rather than
    // emptying the list and re-drawing it.
    placeholderData: keepPreviousData,
  })
}

export function useAnswer() {
  const queryClient = useQueryClient()
  const { actor } = useActor()
  return useMutation({
    mutationFn: async ({ recordId, req }: { recordId: number; req: AnswerRequest }) =>
      (await apiClient.post<AnswerResult>(`/records/${recordId}/answer`,
        { ...reviewerFields(actor), ...req })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['audit'] })
      queryClient.invalidateQueries({ queryKey: ['audit-verify'] })
    },
  })
}

export function useUnresolvable() {
  const queryClient = useQueryClient()
  const { actor } = useActor()
  return useMutation({
    mutationFn: async ({ recordId, req }: { recordId: number; req: UnresolvableRequest }) =>
      (await apiClient.post<AnswerResult>(`/records/${recordId}/unresolvable`,
        { ...reviewerFields(actor), ...req })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['audit'] })
      queryClient.invalidateQueries({ queryKey: ['audit-verify'] })
    },
  })
}
