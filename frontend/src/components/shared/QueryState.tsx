import { Diamond } from './Diamond'
import { TextShimmer } from './TextShimmer'

interface QueryStateProps {
  isLoading: boolean
  isError: boolean
  error?: unknown
  loadingLabel?: string
}

function errorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) return String((error as { message: unknown }).message)
  return 'Request failed'
}

// Shared loading/error presentation so every panel talking to the live API fails the same
// visible way instead of silently rendering nothing.
export function QueryState({ isLoading, isError, error, loadingLabel = 'Loading' }: QueryStateProps) {
  if (isLoading) {
    return (
      <div className="flex h-24 items-center justify-center gap-2.5 text-sm text-stone-500">
        <Diamond className="h-3.5 w-3.5 text-primary-500" />
        <TextShimmer>{loadingLabel}</TextShimmer>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="flex h-24 flex-col items-center justify-center gap-1 rounded-xl bg-rose-50 text-sm text-rose-600">
        <p className="font-medium">Could not reach the API</p>
        <p className="text-xs text-rose-500">{errorMessage(error)}</p>
      </div>
    )
  }
  return null
}
