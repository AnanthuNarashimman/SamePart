// The figures that carry the argument on the landing page.
//
// Every number here is a measured run, not an illustration: the cascade shares come from the
// 3,210-pair rebuild, the baseline comparison from `data/generated/baselines.json`, and the
// retrieval funnel from the 18,611-record scale evaluation. If a run changes, these change.

/** Cascade tiers, cheapest first. Green is settled for free; orange is the only slice that
 *  costs a model call, and its smallness is the whole point of the picture. */
const TIERS = [
  { label: 'Manufacturer part number', pairs: 214, share: 6.7, colour: '#103621', note: 'same maker, same number' },
  { label: 'Attribute agreement', pairs: 2226, share: 69.3, colour: '#2fb85e', note: 'typed values match' },
  { label: 'Conflict gate', pairs: 594, share: 18.5, colour: '#9ff8a2', note: 'a hard rule decided it' },
  { label: 'Language model', pairs: 176, share: 5.5, colour: '#ec9c4c', note: 'genuinely ambiguous' },
] as const

export function CascadeBar() {
  return (
    <div>
      <div className="flex h-14 w-full overflow-hidden rounded-xl">
        {TIERS.map((t) => (
          <div
            key={t.label}
            title={`${t.label} — ${t.pairs.toLocaleString('en-IN')} pairs`}
            style={{ width: `${t.share}%`, backgroundColor: t.colour }}
            className="flex items-center justify-center"
          >
            {t.share > 15 && (
              <span className={`font-mono text-sm font-semibold ${t.colour === '#9ff8a2' ? 'text-brand-900' : 'text-white'}`}>
                {t.share}%
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 flex overflow-hidden rounded-lg border border-stone-200">
        <div className="flex-[94.5] border-r border-stone-200 bg-brand-50 px-3 py-2">
          <p className="text-xs font-semibold tracking-wide text-brand-900">94.5% DECIDED WITHOUT A MODEL</p>
        </div>
        <div className="flex-[5.5] bg-primary-50 px-2 py-2">
          <p className="text-right text-xs font-semibold tracking-wide text-primary-700">5.5%</p>
        </div>
      </div>

      <dl className="mt-6 grid gap-3 sm:grid-cols-2">
        {TIERS.map((t) => (
          <div key={t.label} className="flex items-start gap-3">
            <span className="mt-1.5 h-3 w-3 shrink-0 rounded-sm" style={{ backgroundColor: t.colour }} />
            <div>
              <dt className="text-sm font-medium text-stone-900">{t.label}</dt>
              <dd className="text-xs text-stone-500">
                <span className="font-mono">{t.pairs.toLocaleString('en-IN')}</span> pairs · {t.note}
              </dd>
            </div>
          </div>
        ))}
      </dl>
    </div>
  )
}

/** Wrongly merged share of hard negatives — pairs built to look alike and not be alike.
 *  Lower is better, and the gap between the text-similarity rows and ours is the argument. */
const BASELINES: { name: string; what: string; rate: number; merges: number; ours?: boolean }[] = [
  { name: 'Sentence embeddings', what: 'cosine over the raw description', rate: 64.39, merges: 6794 },
  { name: 'Token Jaccard', what: 'token-set overlap', rate: 59.65, merges: 6294 },
  { name: 'Character trigrams', what: '3-gram overlap', rate: 52.93, merges: 5585 },
  { name: 'A model on raw text', what: 'two descriptions, no attributes, no gates', rate: 5.0, merges: 528 },
  { name: 'Meridian', what: 'typed attributes, gates outside the model', rate: 0.12, merges: 13, ours: true },
]

export function BaselineBars() {
  const max = 64.39
  return (
    <div className="space-y-5">
      {BASELINES.map((b) => (
        <div key={b.name}>
          <div className="mb-1.5 flex items-baseline justify-between gap-4">
            <span className={`text-sm ${b.ours ? 'font-semibold text-brand-100' : 'font-medium text-stone-300'}`}>
              {b.name}
              <span className="ml-2 hidden text-xs font-normal text-stone-500 sm:inline">{b.what}</span>
            </span>
            <span className={`shrink-0 font-mono text-sm font-semibold ${b.ours ? 'text-brand-500' : 'text-stone-400'}`}>
              {b.rate}%
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full"
              style={{
                // A 0.12% bar is a hairline at true scale, so it is floored at something a
                // reader can see. The number beside it carries the exact value.
                width: `${Math.max((b.rate / max) * 100, 1.2)}%`,
                // Brighter than the app's status red, which was tuned against white and sits
                // too close to the section's green ground to read as a bar.
                backgroundColor: b.ours ? '#72f294' : '#f0685f',
              }}
            />
          </div>
          <p className="mt-1 text-xs text-stone-500">
            <span className="font-mono">{b.merges.toLocaleString('en-IN')}</span> wrong merges of 10,551 hard negatives
          </p>
        </div>
      ))}
    </div>
  )
}

/** 173 million comparisons are not run. Blocking removes 99.48% of them and drops nothing. */
export function RetrievalFunnel() {
  const steps = [
    { label: 'Every pair, if compared naively', value: '173,063,710', width: 100, tone: 'bg-white/10' },
    { label: 'Candidate pairs after blocking', value: '902,876', width: 14, tone: 'bg-brand-500/70' },
    { label: 'True pairs missed', value: '0', width: 3, tone: 'bg-brand-500' },
  ]
  return (
    <div className="space-y-4">
      {steps.map((s) => (
        <div key={s.label}>
          <div className="mb-1.5 flex items-baseline justify-between gap-4">
            <span className="text-sm text-stone-300">{s.label}</span>
            <span className="shrink-0 font-mono text-sm font-semibold text-brand-100">{s.value}</span>
          </div>
          <div className={`h-2.5 rounded-full ${s.tone}`} style={{ width: `${s.width}%`, minWidth: '10px' }} />
        </div>
      ))}
    </div>
  )
}

/** The printed code, taken apart. The point of the diagram is which segment is permanent. */
const SEGMENTS: { text: string; label: string; detail: string; permanent?: boolean }[] = [
  { text: 'IN', label: 'country', detail: 'India, NCS code 72' },
  { text: '31161600', label: 'class', detail: 'UNSPSC — may change' },
  { text: '0000417', label: 'identity', detail: 'permanent, never reused', permanent: true },
  { text: '3', label: 'check', detail: 'Luhn digit' },
]

export function NationalCodeAnatomy() {
  return (
    <div>
      <div className="flex flex-wrap items-stretch gap-1.5">
        {SEGMENTS.map((s, i) => (
          <div key={s.label} className="flex items-stretch gap-1.5">
            <div className="flex flex-col items-center">
              <div
                className={`rounded-lg px-3 py-2.5 font-mono text-lg font-semibold tracking-tight sm:text-xl ${
                  s.permanent
                    ? 'bg-brand-900 text-brand-100'
                    : 'bg-white text-stone-800 ring-1 ring-stone-200'
                }`}
              >
                {s.text}
              </div>
              <div className={`mt-2 h-3 w-px ${s.permanent ? 'bg-brand-700' : 'bg-stone-300'}`} />
              <p className={`mt-1 text-[11px] font-semibold uppercase tracking-wide ${s.permanent ? 'text-brand-700' : 'text-stone-400'}`}>
                {s.label}
              </p>
              <p className="max-w-[9rem] text-center text-[11px] leading-snug text-stone-400">{s.detail}</p>
            </div>
            {i < SEGMENTS.length - 1 && (
              <span className="self-start pt-2 font-mono text-lg text-stone-300">–</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/** A gate overruling the model. Drawn rather than described, because "the AI does not get a
 *  vote" is the sentence a refinery engineer is actually listening for. */
export function GateVeto() {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <span className="rounded-md bg-stone-100 px-2 py-1 font-mono text-[11px] font-semibold text-stone-500">MODEL</span>
        <p className="text-sm text-stone-500">
          “These look like the same bolt.” <span className="font-mono text-stone-400">confidence 0.94</span>
        </p>
      </div>

      <div className="my-3 ml-5 h-5 w-px bg-stone-200" />

      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
        <div className="mb-2 flex items-center gap-2">
          <svg viewBox="0 0 24 24" fill="none" stroke="#d03b3b" strokeWidth={2} strokeLinecap="round" className="h-4 w-4">
            <circle cx="12" cy="12" r="9" />
            <path d="m15 9-6 6" />
          </svg>
          <span className="font-mono text-[11px] font-semibold tracking-wide text-rose-700">GATE · property_class</span>
        </div>
        <p className="font-mono text-sm text-stone-700">A2-70 ≠ A4-80</p>
        <p className="mt-1.5 text-sm text-stone-600">
          Different strength grades are different parts. The verdict is overruled, and the
          override is written into the audit trail with the rule that fired.
        </p>
      </div>

      <p className="mt-3 text-xs text-stone-400">
        Gates live in a YAML file a plant engineer can read, outside the model, where they can be
        argued with.
      </p>
    </div>
  )
}
