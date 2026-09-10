// One palette for every chart, so five panels read as one system rather than five widgets.
//
// Chosen by computation, not taste. The app's own brand green and primary orange were tested
// first and FAILED colourblind separation as a categorical set (ΔE 5.4 deutan, against a
// target of 8). That failure pushed a better question: do these charts need categorical
// colour at all? None of them do. Every one is a sequential ramp, a status colour, or a
// single series, which sidesteps the problem entirely rather than working around it.
//
// Validated with the dataviz palette validator:
//   ordinal blues  #86b6ef → #104281   ALL CHECKS PASS (monotone L, one hue, light end 2.06:1)
//   status red     #d03b3b             4.68:1 on white, used alone and always labelled
//
// The light end sits at 2.06:1, which is a deliberate WARN: it obligates visible labels, so
// every chart using it carries direct labels or a legend. That is the mitigation, not an
// oversight.

/** Organisation identity. Fixed slot order, never cycled, and the SAME colour for a given
 *  CPSE on every chart — that consistency is most of what makes panels read as one system.
 *  Validated as a categorical set: worst adjacent pair ΔE 9.1 under protanopia, above the
 *  floor of 8. The app's own green-and-orange failed this at 5.4, which is why these come
 *  from the validated theme instead. */
export const ORG_SLOTS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'] as const

/** The same four identities, stepped for a dark analytical surface. Validated separately
 *  against charcoal rather than flipped from the light set: all four clear 3:1 on #161615 and
 *  the worst adjacent pair holds ΔE 8.4 under protanopia. */
export const ORG_SLOTS_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500'] as const

const orgIndex = new Map<string, number>()
export function orgColour(code: string): string {
  if (!orgIndex.has(code)) orgIndex.set(code, orgIndex.size)
  return ORG_SLOTS[orgIndex.get(code)! % ORG_SLOTS.length]
}

export function orgColourDark(code: string): string {
  if (!orgIndex.has(code)) orgIndex.set(code, orgIndex.size)
  return ORG_SLOTS_DARK[orgIndex.get(code)! % ORG_SLOTS_DARK.length]
}

/** Ordered magnitude. Light means less, dark means more. Never used for identity. */
export const RAMP = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'] as const

/** The single series colour, for charts with exactly one line or one set of marks. */
export const SERIES = '#2a78d6'

/** Reserved. Never a series colour. Always ships with a label beside it. */
export const STATUS = {
  critical: '#d03b3b',
  serious: '#ec835a',
} as const

/** Recessive furniture. Grid and axes must never compete with the marks. */
export const INK = {
  grid: '#f0efec',
  axis: '#a8a29e',
  label: '#57534e',
  muted: '#a8a29e',
  strong: '#1c1917',
} as const

export const TOOLTIP = {
  fontSize: 12,
  borderRadius: 10,
  border: '1px solid #e7e5e4',
  boxShadow: '0 4px 16px -8px rgba(0,0,0,0.2)',
  padding: '8px 10px',
} as const

export const compact = (n: number) =>
  n >= 1e7 ? `${(n / 1e7).toFixed(2)} cr`
    : n >= 1e5 ? `${(n / 1e5).toFixed(1)} L`
      : n >= 1000 ? `${(n / 1000).toFixed(1)}k`
        : `${Math.round(n)}`

/** One unit for a whole axis, picked from its largest value and then used for every tick and
 *  every bar label on that axis.
 *
 *  `compact` above chooses a unit per value, which is right for prose and wrong for a scale:
 *  the stock axis came out reading 1.8 L, 1.4 L, 90.0k, 45.0k, 0 — lakhs and thousands down
 *  one ruler, so neighbouring gridlines could not be compared at a glance. Worse, it rounded
 *  the 1,35,000 gridline to "1.4 L", misstating by 5,000 the very line a reader measures bars
 *  against. Both faults come from deciding the unit per value, so the unit is decided once.
 *
 *  Lakhs only start at ten lakh, because below that thousands stay shorter and exact:
 *  180k beats 1.8 L, and 45k beats 0.45 L. */
export function axisUnit(max: number): (n: number) => string {
  const [div, suffix] =
    max >= 1e7 ? [1e7, ' cr']
      : max >= 1e6 ? [1e5, ' L']
        : max >= 1e3 ? [1e3, 'k']
          : [1, '']
  return (n: number) => {
    if (n === 0) return '0'
    const v = n / div
    // Number() drops a trailing .0, so a round tick stays short while an odd one keeps the
    // digit that tells it apart from its neighbour.
    return `${Number(v.toFixed(Math.abs(v) >= 100 ? 0 : 1))}${suffix}`
  }
}

export const count = (n: number) => n.toLocaleString('en-IN')
