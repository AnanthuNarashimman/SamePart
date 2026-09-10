import { useEffect, useMemo, useState } from 'react'

// One pager, used by every long list in the product.
//
// Scrolling is how a list hides its own size. A reader who has to drag through forty rows to
// reach the panel underneath cannot tell whether they have seen everything, and a screenshot
// of a scrolled list shows an arbitrary slice. A page tells you where you are and how much
// there is, and it makes every list the same shape to read.
//
// It deliberately keeps its own state rather than pushing to the URL: these are panels within
// a page, not routes, and a back button that walked backwards through table pages would be
// worse than no history at all.

export function usePaged<T>(items: T[], perPage: number) {
  const [page, setPage] = useState(0)
  const pages = Math.max(1, Math.ceil(items.length / perPage))

  // A filter or a re-sort can shrink the list under a reader standing on page four, which
  // would otherwise leave them looking at an empty table.
  useEffect(() => {
    if (page > pages - 1) setPage(0)
  }, [page, pages])

  const slice = useMemo(
    () => items.slice(page * perPage, page * perPage + perPage),
    [items, page, perPage],
  )

  return {
    slice,
    page,
    pages,
    setPage,
    from: items.length === 0 ? 0 : page * perPage + 1,
    to: Math.min((page + 1) * perPage, items.length),
    total: items.length,
  }
}

export function Pager({
  page,
  pages,
  from,
  to,
  total,
  unit,
  onPage,
  className = '',
}: {
  page: number
  pages: number
  from: number
  to: number
  total: number
  unit: string
  onPage: (page: number) => void
  className?: string
}) {
  // A single page needs no controls, but the count is still worth saying — "12 of 12" is the
  // reassurance that nothing is hidden.
  const single = pages <= 1

  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 ${className}`}>
      <span className="font-mono text-[11px] tabular-nums text-stone-400">
        {total === 0 ? `no ${unit}` : `${from}–${to} of ${total} ${unit}`}
      </span>

      {!single && (
        <div className="flex items-center gap-1">
          <Step label="Previous" disabled={page === 0} onClick={() => onPage(page - 1)}>
            ‹
          </Step>

          {pageNumbers(page, pages).map((n, i) =>
            n === null ? (
              <span key={`gap-${i}`} className="px-1 font-mono text-[11px] text-stone-300">
                …
              </span>
            ) : (
              <button
                key={n}
                type="button"
                onClick={() => onPage(n)}
                aria-current={n === page ? 'page' : undefined}
                className={`min-w-7 rounded-md px-2 py-1 font-mono text-[11px] tabular-nums
                            transition-colors ${
                  n === page
                    ? 'bg-stone-900 text-white'
                    : 'text-stone-500 hover:bg-stone-100 hover:text-stone-900'
                }`}
              >
                {n + 1}
              </button>
            ),
          )}

          <Step label="Next" disabled={page >= pages - 1} onClick={() => onPage(page + 1)}>
            ›
          </Step>
        </div>
      )}
    </div>
  )
}

function Step({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string
  disabled: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded-md px-2 py-1 text-sm text-stone-500 transition-colors
                 hover:bg-stone-100 hover:text-stone-900
                 disabled:pointer-events-none disabled:text-stone-200"
    >
      {children}
    </button>
  )
}

/** Up to seven slots: first, last, the current neighbourhood, and ellipses for the rest. */
function pageNumbers(page: number, pages: number): (number | null)[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i)

  const out: (number | null)[] = [0]
  const start = Math.max(1, Math.min(page - 1, pages - 4))
  const end = Math.min(pages - 2, Math.max(page + 1, 3))

  if (start > 1) out.push(null)
  for (let n = start; n <= end; n++) out.push(n)
  if (end < pages - 2) out.push(null)
  out.push(pages - 1)
  return out
}
