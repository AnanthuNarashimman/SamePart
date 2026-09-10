export const inr = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(n)

export const pct = (n: number) => `${(n * 100).toFixed(1)}%`

export const VERDICT_LABEL: Record<string, string> = {
  same_material: 'Same material',
  possible_alternative: 'Possible alternative',
  different: 'Different',
  insufficient_evidence: 'Needs input',
}

export const VERDICT_TONE: Record<string, string> = {
  same_material: 'bg-brand-50 text-brand-700',
  possible_alternative: 'bg-khaki-50 text-khaki-700',
  different: 'bg-stone-100 text-stone-500',
  insufficient_evidence: 'bg-rose-50 text-rose-700',
}
