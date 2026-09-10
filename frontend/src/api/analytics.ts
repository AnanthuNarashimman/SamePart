import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type {
  AnalyticsSummary,
  CascadeBreakdown,
  PriceSpreadReport,
  StockAgeing,
  AuditFlagResult,
  RationalisationResult,
  RedistributionReport,
  SavingsResult,
} from './types'

export function useSummary() {
  return useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: async () => (await apiClient.get<AnalyticsSummary>('/analytics/summary')).data,
  })
}

export function useSavings() {
  return useQuery({
    queryKey: ['analytics', 'savings'],
    queryFn: async () => (await apiClient.get<SavingsResult>('/analytics/savings')).data,
  })
}

export function useRationalisation(limit = 100) {
  return useQuery({
    queryKey: ['analytics', 'rationalisation', limit],
    queryFn: async () =>
      (await apiClient.get<RationalisationResult>('/analytics/rationalisation', { params: { limit } })).data,
  })
}

export function useAuditFlags(limit = 50) {
  return useQuery({
    queryKey: ['analytics', 'audit-flags', limit],
    queryFn: async () =>
      (await apiClient.get<AuditFlagResult>('/analytics/audit-flags', { params: { limit } })).data,
  })
}

export function useRedistribution(idleDays = 365, limit = 50) {
  return useQuery({
    queryKey: ['analytics', 'redistribution', idleDays, limit],
    queryFn: async () =>
      (await apiClient.get<RedistributionReport>('/analytics/redistribution', {
        params: { idle_days: idleDays, limit },
      })).data,
  })
}

export function useCascade() {
  return useQuery({
    queryKey: ['analytics', 'cascade'],
    queryFn: async () => (await apiClient.get<CascadeBreakdown>('/analytics/cascade')).data,
  })
}

export function usePriceSpread(limit = 12) {
  return useQuery({
    queryKey: ['analytics', 'price-spread', limit],
    queryFn: async () =>
      (await apiClient.get<PriceSpreadReport>('/analytics/price-spread', { params: { limit } })).data,
  })
}

export function useStockAgeing(idleDays = 365) {
  return useQuery({
    queryKey: ['analytics', 'stock-ageing', idleDays],
    queryFn: async () =>
      (await apiClient.get<StockAgeing>('/analytics/stock-ageing', { params: { idle_days: idleDays } })).data,
  })
}
