import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { FamilyLoadResult, FamilyRemoveResult, FamilySummary, ImportStatus, Org } from './types'

export function useOrgs() {
  return useQuery({
    queryKey: ['orgs'],
    queryFn: async () => (await apiClient.get<Org[]>('/orgs')).data,
  })
}

interface StartImportInput {
  file: File
  orgCode: string
  family: string
  columnMap?: Record<string, string>
}

/** Every family the running dictionary carries. The import form needs it: a file brought in
 *  under the wrong family extracts nothing and reports success. */
export function useFamilies() {
  return useQuery({
    queryKey: ['families'],
    queryFn: async () => (await apiClient.get<FamilySummary[]>('/families')).data,
    staleTime: Infinity,
  })
}

export function useStartImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, orgCode, family, columnMap = {} }: StartImportInput) => {
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

/** Add a family from its YAML. The approver's act; the server refuses anyone else. */
export function useLoadFamily() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ yaml, replace = false }: { yaml: string; replace?: boolean }) =>
      (await apiClient.post<FamilyLoadResult>('/families', yaml, {
        params: replace ? { replace: true } : undefined,
        headers: { 'Content-Type': 'text/plain' },
      })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['families'] })
      queryClient.invalidateQueries({ queryKey: ['audit'] })
      queryClient.invalidateQueries({ queryKey: ['audit-verify'] })
    },
  })
}

/** An existing family's file, to start a new one from. */
export async function fetchFamilyYaml(name: string): Promise<string> {
  return (await apiClient.get<string>(`/families/${name}/yaml`, { responseType: 'text' })).data
}

/** Take a runtime-added family out. Refused while records exist under it unless `purge`;
 *  refused for good once a signed decision references them. */
export function useRemoveFamily() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ name, purge = false }: { name: string; purge?: boolean }) =>
      (await apiClient.delete<FamilyRemoveResult>(`/families/${name}`, {
        params: purge ? { purge: true } : undefined,
      })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['families'] })
      queryClient.invalidateQueries({ queryKey: ['audit'] })
      queryClient.invalidateQueries({ queryKey: ['audit-verify'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
  })
}
