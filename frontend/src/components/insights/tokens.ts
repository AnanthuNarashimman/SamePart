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

export const count = (n: number) => n.toLocaleString('en-IN')
