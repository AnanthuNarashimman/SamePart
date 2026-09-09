import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { AnswerRequest, AnswerResult, QuestionPage, UnresolvableRequest } from './types'

export function useQuestions(params: { cursor?: string; limit?: number } = {}) {
  return useQuery({
    queryKey: ['questions', params],
    queryFn: async () => (await apiClient.get<QuestionPage>('/questions', { params })).data,
  })
}

export function useAnswer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ recordId, req }: { recordId: number; req: AnswerRequest }) =>
      (await apiClient.post<AnswerResult>(`/records/${recordId}/answer`, req)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
    },
  })
}

export function useUnresolvable() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ recordId, req }: { recordId: number; req: UnresolvableRequest }) =>
      (await apiClient.post<AnswerResult>(`/records/${recordId}/unresolvable`, req)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
    },
  })
}
