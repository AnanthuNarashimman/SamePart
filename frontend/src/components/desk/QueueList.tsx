import { useState } from 'react'
import { Pager, usePaged } from '../shared/Paginated'
import type { QueueItem, Verdict } from '../../api/types'
import { VERDICT_TONE } from '../shared/formatters'
import { useActor } from '../../lib/actor'

// Reviewer priority order, not alphabetical — see knowledge/10-frontend-plan.md.
//
// The order depends on who is sitting here. A steward's first job is the questions only
// they can answer; the national approver's is the cross-CPSE confirmations only they can
// give, and for them the questions are somebody else's queue and start collapsed.
type Group = { verdict: Verdict; title: string; hint: string; collapsedByDefault: boolean }

const NEEDS_INPUT: Group = { verdict: 'insufficient_evidence', title: 'Needs input', hint: 'System is stuck and asking a question — highest priority', collapsedByDefault: false }
const ALTERNATIVES: Group = { verdict: 'possible_alternative', title: 'Possible alternatives', hint: 'Substitute relationship, not identity — needs judgment', collapsedByDefault: false }
const MATCHES: Group = { verdict: 'same_material', title: 'Confirmed matches', hint: 'Mostly a quick-approve pass', collapsedByDefault: false }
const DIFFERENT: Group = { verdict: 'different', title: 'Confirmed different', hint: 'Informational, no action needed', collapsedByDefault: true }

const STEWARD_ORDER: Group[] = [NEEDS_INPUT, ALTERNATIVES, MATCHES, DIFFERENT]
const APPROVER_ORDER: Group[] = [
  { ...MATCHES, title: 'Cross-CPSE confirmations', hint: 'Approving one creates a national identifier — the approver\'s own work' },
  ALTERNATIVES,
  { ...NEEDS_INPUT, hint: 'Questions for the owning CPSE\'s steward', collapsedByDefault: true },
  DIFFERENT,
]

interface QueueListProps {
  items: QueueItem[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export function QueueList({ items, selectedId, onSelect }: QueueListProps) {
  const { actor } = useActor()
  const GROUP_ORDER = actor.role === 'national_approver' ? APPROVER_ORDER : STEWARD_ORDER
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(GROUP_ORDER.map((g) => [g.verdict, g.collapsedByDefault])),
  )
  // Switching seats changes which groups start open.
  const [seenRole, setSeenRole] = useState(actor.role)
  if (seenRole !== actor.role) {
    setSeenRole(actor.role)
    setCollapsed(Object.fromEntries(GROUP_ORDER.map((g) => [g.verdict, g.collapsedByDefault])))
  }

  return (
    <div className="flex flex-col gap-4">
      {GROUP_ORDER.map((group) => {
        const groupItems = items.filter((i) => i.verdict === group.verdict)
        if (groupItems.length === 0) return null
        return (
          <QueueGroup
            key={group.verdict}
            group={group}
            groupItems={groupItems}
            collapsed={collapsed[group.verdict]}
            onToggle={() =>
              setCollapsed((c) => ({ ...c, [group.verdict]: !c[group.verdict] }))}
            selectedId={selectedId}
            onSelect={onSelect}
          />
        )
      })}
    </div>
  )
}

/** One verdict group, paging independently.
 *
 *  Its own component because a hook cannot live inside a `.map()`, and because each group
 *  needs its own page position: "confirmed different" alone runs to thousands of pairs, and a
 *  reviewer working the queue is only ever inside one group at a time.
 */
function QueueGroup({
  group, groupItems, collapsed: isCollapsed, onToggle, selectedId, onSelect,
}: {
  group: Group
  groupItems: QueueItem[]
  collapsed: boolean
  onToggle: () => void
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  const paged = usePaged(groupItems, 10)

  return (
        <div className="rounded-2xl border border-stone-100 bg-white shadow-sm">
            <button
              type="button"
              onClick={onToggle}
              className="flex w-full items-center justify-between px-4 py-3"
            >
              <span className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${VERDICT_TONE[group.verdict]}`}>
                  {groupItems.length}
                </span>
                <span className="text-sm font-semibold text-stone-900">{group.title}</span>
                <span className="hidden text-xs text-stone-400 sm:inline">· {group.hint}</span>
              </span>
              <span className="text-stone-400">{isCollapsed ? '+' : '−'}</span>
            </button>

            {!isCollapsed && (
              <ul className="flex flex-col divide-y divide-stone-100 border-t border-stone-100">
                {paged.slice.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(item.id)}
                      className={`flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors ${
                        selectedId === item.id ? 'bg-primary-50' : 'hover:bg-stone-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-medium text-stone-400">
                          {item.a_org} &harr; {item.b_org}
                        </span>
                        <span className="text-xs text-stone-300">#{item.id}</span>
                      </div>
                      <p className="truncate text-sm text-stone-700" title={item.a_description}>{item.a_description}</p>
                      <p className="truncate text-xs text-stone-400" title={item.b_description}>{item.b_description}</p>
                      <p className="mt-0.5 truncate text-xs font-medium text-stone-500" title={item.headline}>
                        {item.headline}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {!isCollapsed && (
              <Pager
                page={paged.page} pages={paged.pages} from={paged.from} to={paged.to}
                total={paged.total} unit="pairs" onPage={paged.setPage}
                className="border-t border-stone-100 px-4 py-2.5"
              />
            )}
        </div>
  )
}
