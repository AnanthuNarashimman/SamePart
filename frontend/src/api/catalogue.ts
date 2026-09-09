import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { ImportStatus, Org } from './types'

export function useOrgs() {
  return useQuery({
    queryKey: ['orgs'],
    queryFn: async () => (await apiClient.get<Org[]>('/orgs')).data,
  })
}

interface StartImportInput {
  file: File
  orgCode: string
  family?: string
  columnMap?: Record<string, string>
}

export function useStartImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, orgCode, family = 'hex_bolt', columnMap = {} }: StartImportInput) => {
      const form = new FormData()
      form.append('file', file)
      form.append('org_code', orgCode)
      form.append('family', family)
      form.append('column_map', JSON.stringify(columnMap))
      return (await apiClient.post<ImportStatus>('/imports', form)).data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orgs'] }),
  })
}

export function useImportStatus(importId: string | null) {
  return useQuery({
    queryKey: ['import', importId],
    queryFn: async () => (await apiClient.get<ImportStatus>(`/imports/${importId}`)).data,
    enabled: importId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && !['done', 'failed', 'complete'].includes(status) ? 1500 : false
    },
  })
}
