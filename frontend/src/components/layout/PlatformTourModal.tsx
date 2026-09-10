import { useEffect, useState } from 'react'

interface TourStep {
  eyebrow: string
  title: string
  body: string
  mockup: React.ReactNode
}

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4 sm:p-5">
      <div className="mb-2 flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-rose-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-khaki-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-brand-500" />
        <span className="ml-2 text-[10px] font-medium uppercase tracking-wide text-stone-400">
          Preview · illustrative, not live data
        </span>
      </div>
      <div className="rounded-xl border border-stone-100 bg-white p-4 shadow-sm">{children}</div>
    </div>
  )
}

const MOCK_STAT = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-lg border border-stone-100 bg-white p-2.5">
    <p className="text-[9px] font-medium text-stone-400">{label}</p>
    <p className="text-sm font-semibold text-stone-900">{value}</p>
  </div>
)

const STEPS: TourStep[] = [
  {
    eyebrow: 'Welcome',
    title: 'One dashboard, every CPSE',
    body: 'Meridian pulls every connected organisation’s material master into one place, so you can see how much duplication is hiding across catalogues before you fix any of it.',
    mockup: (
      <Frame>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold text-stone-900">Dashboard</p>
          <span className="h-5 w-5 rounded-full bg-primary-500" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          <MOCK_STAT label="Records imported" value="12,480" />
          <MOCK_STAT label="Canonical materials" value="8,912" />
          <MOCK_STAT label="Duplicates merged" value="1,204" />
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-stone-100">
          <div className="flex h-full w-full">
            <div className="h-full w-[45%] bg-brand-500" />
            <div className="h-full w-[30%] bg-khaki-400" />
            <div className="h-full w-[25%] bg-rose-300" />
          </div>
        </div>
      </Frame>
    ),
  },
  {
    eyebrow: 'Import · step 1',
    title: 'Bring in a catalogue file',
    body: 'Pick which CPSE a file belongs to and drop in its CSV. Meridian reads the real header row from the file itself — nothing about the source is hardcoded.',
    mockup: (
      <Frame>
        <p className="mb-2 text-xs font-semibold text-stone-900">1. Choose source and file</p>
        <div className="flex items-center gap-2">
          <div className="rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-[10px] text-stone-600">
            CPSE-Alpha (CPA)
          </div>
          <div className="flex-1 rounded-lg border border-dashed border-primary-300 px-3 py-1.5 text-center text-[10px] text-primary-600">
            catalogue_march.csv
          </div>
        </div>
        <p className="mt-2 text-[9px] text-stone-400">
          Column names are detected from the header row and mapped in the next step.
        </p>
      </Frame>
    ),
  },
  {
    eyebrow: 'Import · step 2',
    title: 'Map columns, not code',
    body: 'Every source calls things something different. Line each of their columns up against Meridian’s fields once — description, source code, unit — and the mapping is reused for that source.',
    mockup: (
      <Frame>
        <p className="mb-2 text-xs font-semibold text-stone-900">Column mapping</p>
        <div className="space-y-1.5">
          {[
            ['MAT_DESC', 'Description'],
            ['MAT_NO', 'Source code'],
            ['UOM', 'Unit'],
          ].map(([src, dst]) => (
            <div key={src} className="flex items-center gap-2 text-[10px]">
              <span className="w-24 truncate rounded-md bg-stone-100 px-2 py-1 font-mono text-stone-600">{src}</span>
              <span className="text-stone-300">→</span>
              <span className="flex-1 rounded-md border border-brand-300 bg-brand-50 px-2 py-1 text-brand-700">{dst}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-[9px] text-stone-400">3 of 3 columns mapped</p>
          <span className="rounded-lg bg-primary-500 px-3 py-1.5 text-[10px] font-medium text-white">Start import</span>
        </div>
      </Frame>
    ),
  },
  {
    eyebrow: 'Reconciliation · step 1',
    title: 'Work a prioritised queue',
    body: 'Once extraction and matching finish, candidate pairs land in the reconciliation desk — sorted by what actually needs a human, not alphabetically.',
    mockup: (
      <Frame>
        <div className="mb-3 grid grid-cols-3 gap-2">
          <MOCK_STAT label="Needs input" value="14" />
          <MOCK_STAT label="Possible alt." value="9" />
          <MOCK_STAT label="Confirmed" value="37" />
        </div>
        <div className="space-y-1.5">
          {[
            ['M6 HEX BOLT, ZINC PLATED', 'insufficient_evidence', 'bg-rose-50 text-rose-700'],
            ['BALL BEARING 6203-2RS', 'possible_alternative', 'bg-khaki-100 text-khaki-700'],
            ['GASKET, NBR, 40x2mm', 'same_material', 'bg-brand-50 text-brand-700'],
          ].map(([label, tag, cls]) => (
            <div key={label} className="flex items-center justify-between rounded-lg border border-stone-100 px-2.5 py-1.5">
              <span className="truncate text-[10px] text-stone-700">{label}</span>
              <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${cls}`}>{tag}</span>
            </div>
          ))}
        </div>
      </Frame>
    ),
  },
  {
    eyebrow: 'Reconciliation · step 2',
    title: 'Compare, then decide — you decide',
    body: 'Attributes sit side by side with agreement highlighted. Retrieval only proposes the pair; a conflict gate can veto it, and only a person confirms same material, different, or asks a clarifying question.',
    mockup: (
      <Frame>
        <p className="mb-2 text-xs font-semibold text-stone-900">Attribute comparison</p>
        <div className="space-y-1 text-[10px]">
          {[
            ['Diameter', '6 mm', '6 mm', true],
            ['Grade', '8.8', '10.9', false],
            ['Coating', 'Zinc', 'unknown', false],
          ].map(([attr, a, b, agree]) => (
            <div
              key={attr as string}
              className={`grid grid-cols-3 gap-2 rounded-md px-2 py-1 ${agree ? '' : 'bg-rose-50/60'}`}
            >
              <span className="text-stone-400">{attr as string}</span>
              <span className="text-stone-700">{a as string}</span>
              <span className="text-stone-700">{b as string}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex justify-end gap-1.5">
          <span className="rounded-lg bg-stone-100 px-2.5 py-1.5 text-[10px] font-medium text-stone-500">Ask a question</span>
          <span className="rounded-lg bg-rose-100 px-2.5 py-1.5 text-[10px] font-medium text-rose-700">Different</span>
          <span className="rounded-lg bg-brand-500 px-2.5 py-1.5 text-[10px] font-medium text-white">Same material</span>
        </div>
      </Frame>
    ),
  },
  {
    eyebrow: 'You’re set',
    title: 'That’s the core loop',
    body: 'Import a source, map its columns once, then work the reconciliation queue the pipeline builds for you. Duplicate check and the relationship graph are there whenever you need to sanity-check a single part.',
    mockup: (
      <Frame>
        <div className="space-y-2">
          {[
            'Import a CPSE catalogue and map its columns',
            'Let extraction and matching build the queue',
            'Compare, then confirm same, different, or ask',
          ].map((line) => (
            <div key={line} className="flex items-center gap-2 text-[11px] text-stone-700">
              <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brand-500 text-[9px] font-bold text-white">
                ✓
              </span>
              {line}
            </div>
          ))}
        </div>
      </Frame>
    ),
  },
]

const AUTOPLAY_MS = 4500

export function PlatformTourModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (open) {
      setStep(0)
      setPaused(false)
    }
  }, [open])

  // Auto-advance, looping; restarts the countdown whenever the step changes,
  // whether that change came from this timer or from the user clicking a control.
  useEffect(() => {
    if (!open || paused) return
    const id = setTimeout(() => {
      setStep((s) => (s + 1) % STEPS.length)
    }, AUTOPLAY_MS)
    return () => clearTimeout(id)
  }, [open, paused, step])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') setStep((s) => Math.min(s + 1, STEPS.length - 1))
      if (e.key === 'ArrowLeft') setStep((s) => Math.max(s - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm" onClick={onClose} />

      <div
        className="relative flex w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-xl"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        <div className="flex items-start justify-between gap-4 border-b border-stone-100 px-6 pt-5 pb-4">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-primary-600">{current.eyebrow}</p>
            <h2 className="mt-0.5 text-lg font-semibold text-stone-900">{current.title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close tour"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-stone-400 hover:bg-stone-100 hover:text-stone-700"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" className="h-4 w-4">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        {/* Fixed-height viewport: every step is the same size, so the panel never resizes as steps change. */}
        <div className="h-[430px] overflow-hidden sm:h-[400px]">
          <div
            className="flex h-full transition-transform duration-500 ease-in-out"
            style={{ transform: `translateX(-${step * 100}%)` }}
          >
            {STEPS.map((s) => (
              <div key={s.title} className="scroll-clean h-full w-full shrink-0 overflow-y-auto px-6 py-5">
                <p className="mb-4 text-sm leading-relaxed text-stone-600">{s.body}</p>
                {s.mockup}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-stone-100 px-6 py-4">
          <div className="flex items-center gap-1.5">
            {STEPS.map((s, i) => (
              <button
                key={s.title}
                type="button"
                aria-label={`Go to step ${i + 1}`}
                onClick={() => setStep(i)}
                className={`h-1.5 rounded-full transition-all ${
                  i === step ? 'w-5 bg-primary-500' : 'w-1.5 bg-stone-200 hover:bg-stone-300'
                }`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-stone-500 hover:bg-stone-100 hover:text-stone-800"
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={() => (isLast ? onClose() : setStep((s) => s + 1))}
              className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
            >
              {isLast ? 'Start using Meridian' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
