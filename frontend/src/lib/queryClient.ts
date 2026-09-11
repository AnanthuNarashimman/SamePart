import { QueryClient } from '@tanstack/react-query'

/** Reviewing a queue means walking between pages and back all day. On React Query's own
 *  defaults every one of those returns is a cold refetch — data is stale the moment it
 *  lands, so remounting a page re-fetches it and the content blanks under a spinner.
 *  A minute of freshness covers that walk; anything a mutation changes is invalidated
 *  explicitly at the call site, so this never serves a stale decision. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
})
