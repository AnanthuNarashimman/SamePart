import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { AuditTrail, ChainStatus } from './types'

export function useAuditTrail(params: { actor?: string; action?: string; limit?: number } = {}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn: async () => (await apiClient.get<AuditTrail>('/audit', { params })).data,
  })
}

/** Whether the chain has been altered since it was written. Anyone may ask; nobody can fake it. */
export function useAuditVerify() {
  return useQuery({
    queryKey: ['audit-verify'],
    queryFn: async () => (await apiClient.get<ChainStatus>('/audit/verify')).data,
  })
}
