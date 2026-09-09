import { useMutation } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { CheckRequest, CheckResult } from './types'

export function useCheck() {
  return useMutation({
    mutationFn: async (req: CheckRequest) => (await apiClient.post<CheckResult>('/check', req)).data,
  })
}
