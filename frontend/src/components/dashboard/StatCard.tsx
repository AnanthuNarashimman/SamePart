interface StatCardProps {
  label: string
  value: string
  hint?: string
  accent?: 'default' | 'dark'
}

export function StatCard({ label, value, hint, accent = 'default' }: StatCardProps) {
  const isDark = accent === 'dark'
  return (
    <div
      className={`rounded-2xl p-5 shadow-sm ${
        isDark
          ? 'bg-gradient-to-br from-brand-500 to-brand-700 text-white'
          : 'border border-stone-100 bg-white text-stone-900'
      }`}
    >
      <p className={`text-xs font-medium ${isDark ? 'text-white/70' : 'text-stone-400'}`}>
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      {hint && (
        <p className={`mt-1 text-xs ${isDark ? 'text-white/60' : 'text-stone-400'}`}>{hint}</p>
      )}
    </div>
  )
}
