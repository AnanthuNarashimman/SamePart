import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from 'react'
import { Link } from 'react-router-dom'
import { ConvergenceHero } from '../components/landing/ConvergenceHero'
import {
  BaselineBars,
  CascadeBar,
  GateVeto,
  NationalCodeAnatomy,
  RetrievalFunnel,
} from '../components/landing/figures'
import { BallBearing, BallValve, HexBolt, SpiralGasket } from '../components/landing/parts'
import { ProblemStage } from '../components/landing/ProblemStage'

// The public face of the project, told in the order the argument actually lands: the four
// lists diverge, that invisibility costs money, here is how identity is decided, here is the
// proof against the obvious alternatives, here is what it is worth, and here is why nobody
// has to give anything up to get it.
//
// Every figure on this page is a measured run over the simulated catalogue, and the page says
// so in its own footer rather than waiting to be asked.

const NAV = [
  { label: 'The problem', href: '#divergence' },
  { label: 'How it decides', href: '#cascade' },
  { label: 'Evidence', href: '#evidence' },
  { label: 'Impact', href: '#impact' },
] as const

/** The four families the dictionaries declare, and the whole of what the catalogue covers. */
const FAMILIES = [
  { name: 'Hex bolts', Part: HexBolt },
  { name: 'Ball bearings', Part: BallBearing },
  { name: 'Spiral wound gaskets', Part: SpiralGasket },
  { name: 'Ball valves', Part: BallValve },
] as const

const VERDICTS = [
  {
    verdict: 'Same part',
    body: 'Every critical attribute agrees and the evidence for each one is recorded against the words that proved it.',
    tone: 'brand',
  },
  {
    verdict: 'Different part',
    body: 'A declared attribute disagrees. Often a gate reached this before any model was consulted.',
    tone: 'stone',
  },
  {
    verdict: 'Possible substitute',
    body: 'Not the same item, but interchangeable — and the conditions under which that holds are stated, not implied.',
    tone: 'khaki',
  },
  {
    verdict: 'Not enough information',
    body: 'A critical attribute is missing from both records. The system asks the steward who would know instead of guessing.',
    tone: 'primary',
  },
] as const

export function Landing() {
  const scroller = useRef<HTMLDivElement>(null)
  const navHidden = useHideOnScrollDown(scroller)
  const { progress, reduced } = useIntroProgress(scroller)

  return (
    <div ref={scroller} className="scroll-clean h-full overflow-y-auto scroll-smooth bg-[#fbfaf7] text-stone-900">
      <Nav hidden={navHidden} />
      <Hero progress={progress} reduced={reduced} />
      <Divergence scroller={scroller} />
      <Cost />
      <Cascade />
      <Verdicts />
      <Gates />
      <Evidence />
      <Additive />
      <Impact />
      <Close />
      <Footer />
    </div>
  )
}

/** How far the reader scrolls to play the hero's opening. The hero section carries exactly this
 *  much height below its sticky viewport, so the intro finishes at the moment the card unsticks. */
const INTRO_VH = 95

/** 0 → 1 across that distance, clamped at both ends. Drives the hero's opening: the page starts
 *  as the illustration alone and assembles into the hero as the reader scrolls.
 *
 *  Reads are coalesced into an animation frame, because a scroll handler that calls setState on
 *  every event will fire several times per frame for nothing.
 *
 *  Under a reduced-motion preference the intro does not exist: progress is pinned at 1 and the
 *  hero renders assembled, with no extra scroll to get through. */
function useIntroProgress(ref: RefObject<HTMLDivElement | null>) {
  const reduced =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [progress, setProgress] = useState(reduced ? 1 : 0)

  useEffect(() => {
    const el = ref.current
    if (!el || reduced) return
    let frame = 0

    const read = () => {
      frame = 0
      const distance = Math.max(320, (window.innerHeight * INTRO_VH) / 100)
      setProgress(Math.min(1, Math.max(0, el.scrollTop / distance)))
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(read)
    }

    read()
    el.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      el.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [ref, reduced])

  return { progress, reduced }
}

/** How far a section has travelled through its own sticky range, 0 → 1. Where `useIntroProgress`
 *  measures from the top of the page, this measures a section wherever it happens to sit, so a
 *  tall section with sticky contents can drive something as the reader scrolls through it.
 *
 *  The page scrolls inside a div that fills the viewport and starts at its top, so the section's
 *  own `getBoundingClientRect().top` is already the distance scrolled into it. */
function useSectionProgress(
  scroller: RefObject<HTMLDivElement | null>,
  section: RefObject<HTMLElement | null>,
) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const scrollEl = scroller.current
    const el = section.current
    if (!scrollEl || !el) return
    let frame = 0

    const read = () => {
      frame = 0
      const travel = Math.max(1, el.offsetHeight - window.innerHeight)
      setProgress(Math.min(1, Math.max(0, -el.getBoundingClientRect().top / travel)))
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(read)
    }

    read()
    scrollEl.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      scrollEl.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [scroller, section])

  return progress
}

/** Progress remapped to 0-1 across a sub-range, so each element can start and finish at its own
 *  point in the intro rather than all of them moving together. */
const ramp = (p: number, from: number, to: number) =>
  Math.min(1, Math.max(0, (p - from) / (to - from)))

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

/** Smoothstep. Eases both ends, so the illustration settles rather than stopping dead. */
const ease = (t: number) => t * t * (3 - 2 * t)

/** Hides the pill while the reader is moving down the page and brings it back on the first
 *  hint of movement back up. The thresholds are deliberately lopsided: it takes a real downward
 *  push to dismiss the pill, but a nudge upward to recall it, which is the asymmetry that makes
 *  the behaviour feel obedient rather than twitchy. The page scrolls inside a div rather than
 *  the window, so the listener goes on that element. */
function useHideOnScrollDown(ref: RefObject<HTMLDivElement | null>) {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let last = el.scrollTop

    const onScroll = () => {
      const y = el.scrollTop
      const delta = y - last
      // Over the hero the pill belongs to the card, so it is never taken away there.
      if (y < 90) setHidden(false)
      else if (delta > 8) setHidden(true)
      else if (delta < -4) setHidden(false)
      last = y
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [ref])

  return hidden
}

// A pill floating clear of the page rather than a bar welded to its top edge. It is fixed to
// the viewport, so the wrapper is made click-through and only the pill itself takes pointer
// events — otherwise an invisible full-width strip would swallow clicks across the hero.
function Nav({ hidden }: { hidden: boolean }) {
  return (
    <div
      className={`pointer-events-none fixed inset-x-0 top-6 z-50 flex justify-center px-4 transition-all duration-300 ease-out ${
        hidden ? '-translate-y-24 opacity-0' : 'translate-y-0 opacity-100'
      }`}
    >
      {/* The pill floats over both the dark hero card and the light sections below it, so the
          ground has to be near-opaque — at 75% the stone text was reading against whatever
          happened to be behind it. */}
      <header className="pointer-events-auto flex w-full max-w-3xl items-center justify-between gap-3 rounded-full border border-stone-900/10 bg-white/92 py-2 pr-2 pl-4 shadow-[0_10px_34px_-14px_rgba(28,25,23,0.32)] backdrop-blur-xl">
        <a href="#top" className="flex shrink-0 items-center gap-2">
          <img src="/logo.png" alt="" className="h-7 w-7 shrink-0 object-contain" />
          <span className="font-display text-lg tracking-tight">Meridian</span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="rounded-full px-3 py-1.5 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-900/5 hover:text-stone-900"
            >
              {n.label}
            </a>
          ))}
        </nav>

        <Link
          to="/login"
          className="shrink-0 rounded-full bg-brand-900 px-4 py-2 text-sm font-medium text-brand-100 transition-colors hover:bg-stone-900"
        >
          Sign in
        </Link>
      </header>
    </div>
  )
}

// The opening. On load the card holds nothing but the illustration, sized up and sitting on the
// card's centre line: four records converging through the mark into one code, and not a word of
// prose anywhere. Scrolling assembles the hero around it — the illustration rises and settles to
// its normal size while the headline, the copy and the figures arrive after it, each on its own
// slice of the scroll.
//
// The section is taller than the viewport and its contents are sticky, so this plays out in
// place rather than scrolling past. The extra height matches the intro distance exactly, which
// means the illustration reaches its resting position at the same moment the card unsticks.
//
// The card's top gutter is deliberately smaller than the pill's own offset, so the pill lands
// inside the card rather than above it.
function Hero({ progress, reduced }: { progress: number; reduced: boolean }) {
  // Everything below the illustration is measured rather than guessed. With the content block
  // centred in the card, moving the illustration down by half that height would put it exactly on
  // the card's centre line; it is held slightly short of that because the full distance makes for
  // an uncomfortably long climb once the reader starts scrolling.
  //
  // Measured in a layout effect, not an ordinary one: the first paint has to already carry the
  // offset, or the illustration is briefly drawn at its resting position and then jumps down.
  const below = useRef<HTMLDivElement>(null)
  const [shift, setShift] = useState(0)

  useLayoutEffect(() => {
    const el = below.current
    if (!el) return
    const measure = () => setShift(el.offsetHeight * 0.42)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const settle = ease(ramp(progress, 0, 0.72))
  const artStyle = { '--p': settle, '--shift': `${shift}px` } as CSSProperties

  const copy = ramp(progress, 0.34, 0.76)
  const copyStyle: CSSProperties = {
    opacity: copy,
    transform: `translateY(${lerp(26, 0, ease(copy))}px)`,
  }

  const figures = ramp(progress, 0.58, 1)
  const figureStyle: CSSProperties = {
    opacity: figures,
    transform: `translateY(${lerp(22, 0, ease(figures))}px)`,
  }

  return (
    <section
      id="top"
      className="relative"
      style={reduced ? undefined : { height: `calc(100dvh + ${INTRO_VH}vh)` }}
    >
      <div className="sticky top-0 h-dvh px-3 pt-3 pb-4 sm:px-4 sm:pb-5 lg:px-5">
        <div className="hero-card relative flex h-full flex-col items-center justify-center overflow-hidden rounded-[1.5rem] border border-white/8 px-4 pt-16 pb-10 text-center shadow-[0_30px_70px_-45px_rgba(13,39,24,0.7)] sm:rounded-2xl sm:px-8 sm:pt-16 sm:pb-12">
          <div className="hero-grid pointer-events-none absolute inset-0" />
          <CornerDots corner="tl" />
          <CornerDots corner="tr" />
          <CornerDots corner="bl" />
          <CornerDots corner="br" />

          {/* The name half-sunk in the card's bottom edge, the same treatment the closing
              section ends on. It gives the opening screen something to sit above, and it goes
              under completely as the hero assembles — by the time the figures arrive the card
              is back to the resting layout, which carries no wordmark. */}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center overflow-hidden">
            <span
              className="font-sans text-[15vw] leading-none font-extrabold tracking-[0.03em] whitespace-nowrap text-white/8 select-none"
              style={{ transform: `translateY(${lerp(30, 120, settle)}%)` }}
            >
              MERIDIAN
            </span>
          </div>

          <div className="relative w-full">
            <div className="hero-art" style={artStyle}>
              <ConvergenceHero captionOpacity={copy} assembled={settle} />
            </div>

            {/* Padding rather than a margin, so the gap above counts toward the measured height. */}
            <div ref={below} className="pt-5 sm:pt-6">
              <div className="mx-auto max-w-3xl" style={copyStyle}>
                <p className="text-[11px] font-semibold tracking-[0.18em] text-brand-500 uppercase sm:text-xs">
                  SIH26099 · Material codes across CPSEs
                </p>

                {/* The chip is kept to a tight line-height and light vertical padding so it stays
                    inside the headline's own line box instead of prising the two lines apart. */}
                <h1 className="mt-5 font-display text-[1.95rem] leading-[1.22] tracking-tight text-white sm:mt-6 sm:text-[2.7rem] lg:text-[3.3rem]">
                  Different codes. One part.
                  <br />
                  One{' '}
                  <span className="inline-block rounded-xl bg-brand-500 px-3 py-0.5 leading-[1.05] tracking-normal text-brand-900 sm:rounded-2xl sm:px-4 sm:py-1">
                    Meridian
                  </span>
                  .
                </h1>

                <p className="mx-auto mt-5 max-w-md text-sm leading-relaxed text-stone-400 sm:text-[15px]">
                  Meridian finds the entries that are secretly the same part, gives each one a
                  national code, and{' '}
                  <strong className="font-semibold text-stone-100">never touches anyone's own code</strong>.
                </p>

                {/* Each carries the shape of what it does: an arrow leading out of the page for
                    the one that signs you in, a chevron pointing down the page for the one that
                    scrolls to the proof. */}
                <div className="mt-7 flex flex-wrap justify-center gap-3">
                  <Link
                    to="/login"
                    className="group inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-semibold text-brand-900 shadow-[0_8px_22px_-16px_rgba(114,242,148,0.7)] transition-all hover:bg-brand-300 hover:shadow-[0_12px_28px_-16px_rgba(114,242,148,0.85)] focus-visible:ring-2 focus-visible:ring-brand-300 focus-visible:outline-none"
                  >
                    Enter the platform
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2.2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5"
                    >
                      <path d="M5 12h13M12 5l7 7-7 7" />
                    </svg>
                  </Link>

                  <a
                    href="#evidence"
                    className="group inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/5 px-5 py-3 text-sm font-medium text-stone-200 backdrop-blur-sm transition-colors hover:border-white/40 hover:bg-white/10 hover:text-white focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:outline-none"
                  >
                    See the evidence
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2.2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="h-4 w-4 text-stone-400 transition-all duration-200 group-hover:translate-y-0.5 group-hover:text-stone-200"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </a>
                </div>
              </div>

              <dl
                className="mx-auto mt-6 grid max-w-3xl grid-cols-2 gap-x-4 gap-y-4 border-t border-white/10 pt-4 sm:grid-cols-4"
                style={figureStyle}
              >
                {[
                  ['18,611', 'records evaluated'],
                  ['99.48%', 'of comparisons never run'],
                  ['0', 'true pairs missed by blocking'],
                  ['94.5%', 'decided without a model'],
                ].map(([value, label]) => (
                  <div key={label}>
                    <dt className="font-display text-2xl leading-none tracking-tight text-white sm:text-[1.75rem]">
                      {value}
                    </dt>
                    <dd className="mt-1.5 text-[11px] leading-snug text-stone-400">{label}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}

function Divergence({ scroller }: { scroller: RefObject<HTMLDivElement | null> }) {
  // The stage locks in view with the screen dead, and the reader's own scrolling throws the
  // switch partway through it.
  //
  // The toggle in the title bar still works, without the two fighting each other: a click records
  // the scroll state it was made against, and that override applies only while the scroll state
  // has not moved on. So a manual flip holds until the reader crosses the threshold, and then
  // scrolling takes over again. Derived during render rather than synced in an effect, which
  // would have meant writing state on every crossing.
  const stage = useRef<HTMLDivElement>(null)
  const stageProgress = useSectionProgress(scroller, stage)
  const [override, setOverride] = useState<{ at: boolean; value: boolean } | null>(null)

  const scrolledOn = stageProgress > 0.45
  const on = override?.at === scrolledOn ? override.value : scrolledOn
  const toggle = () => setOverride({ at: scrolledOn, value: !on })

  // No `overflow-hidden` on the section, deliberately: it would become the scrolling ancestor for
  // the sticky stage below and the lock would silently stop working. Nothing here overflows its
  // bounds, so the clip was not buying anything.
  return (
    <section
      id="divergence"
      className="stage-surface relative scroll-mt-24 border-y border-stone-900/8"
    >
      <FallingDots />
      <div className="relative mx-auto max-w-6xl px-5 pt-16 sm:px-8 lg:pt-20">
        <Eyebrow>01 — The problem</Eyebrow>
        <h2 className="mt-4 mb-6 max-w-3xl font-display text-4xl leading-[1.08] tracking-tight sm:text-5xl">
          The same bolt, written differently everywhere
        </h2>
        <p className="max-w-2xl text-[15px] leading-relaxed text-stone-600">
          One bolt, sitting in four systems that cannot talk to each other. None of the four is
          wrong — each house style is decades old, embedded in an ERP, printed on bin labels and
          understood by its own stores team, which is exactly why nobody is going to abandon
          theirs. What no one can see is that it is the same bolt.
        </p>
      </div>

      {/* Held in view long enough to be read off and then operated. Only from `lg`, where the
          stage fits a viewport; narrower than that it is an ordinary block and the switch still
          throws as the reader scrolls past it. */}
      <div ref={stage} className="relative lg:h-[calc(100dvh+80vh)]">
        <div className="mx-auto max-w-6xl px-5 pt-10 sm:px-8 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:items-center lg:pt-0">
          <div className="w-full">
            <ProblemStage on={on} onToggle={toggle} />
          </div>
        </div>
      </div>

      <div className="relative mx-auto max-w-6xl px-5 pb-16 sm:px-8 lg:pb-20">
        <p className="mx-auto max-w-2xl text-center text-[15px] leading-relaxed text-stone-600">
          The messy text is not the problem. The messy text is why the problem exists.{' '}
          <strong className="font-semibold text-stone-900">
            The problem is the invisibility
          </strong>{' '}
          — the duplicate buying and the dead stock that nobody can be shown.
        </p>

        <div className="mt-10 rounded-2xl border border-stone-200 bg-white/70 px-5 py-7 backdrop-blur-sm sm:px-8">
          <p className="text-center text-[11px] font-semibold tracking-[0.16em] text-stone-400 uppercase">
            Four families in the catalogue
          </p>
          <p className="mt-2 text-center text-xs text-stone-400">
            each one declared as a dictionary file, not written into the code
          </p>
          <div className="mt-7 grid grid-cols-2 gap-y-7 sm:grid-cols-4">
            {FAMILIES.map(({ name, Part }, i) => (
              <div
                key={name}
                // The colour is set unconditionally because Tailwind v4 defaults a bare
                // `border-l` to currentColor — without it the dividers took the text colour.
                className={`flex flex-col items-center gap-3 border-stone-200 px-2 text-center ${
                  i % 2 === 1 ? 'border-l' : ''
                } sm:border-l sm:first:border-l-0`}
              >
                <Part className="h-9 w-9 text-brand-700" />
                <span className="text-[13px] leading-snug text-stone-600">{name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function Cost() {
  return (
    <section className="cost-surface relative overflow-hidden border-y border-stone-900/8">
      <FloatingRupees />
      <div className="relative mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:gap-14">
          <div>
            <Eyebrow>What invisibility costs</Eyebrow>
            <p className="mt-5 font-display text-5xl leading-none tracking-tight text-brand-900 sm:text-6xl">
              ₹12,743
              <span className="ml-2 text-2xl sm:text-3xl">crore</span>
            </p>
            <p className="mt-3 max-w-md text-[15px] leading-relaxed text-stone-600">
              of losses over seven years from procurement and inventory management at a single
              public-sector enterprise — audited by the Comptroller and Auditor General and laid
              before Parliament in July 2025.
            </p>
            <p className="mt-3 text-xs text-stone-400">CAG Report No. 10 of 2025, on SAIL.</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:content-center">
            {[
              ['44.3%', 'of the master is duplicate codes', 'measured across the four catalogues'],
              ['19.0%', 'of codes are dead weight', '124 of 654 with no order in four years'],
              ['177', 'vendor part numbers shared', 'across codes nobody had linked'],
            ].map(([big, label, note]) => (
              <div key={label} className="rounded-2xl border border-stone-200 bg-white/75 p-5 backdrop-blur-sm">
                <p className="font-display text-3xl tracking-tight text-stone-900">{big}</p>
                <p className="mt-2 text-sm font-medium text-stone-700">{label}</p>
                <p className="mt-1 text-xs leading-snug text-stone-400">{note}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function Cascade() {
  return (
    <Section id="cascade" n="02" kicker="How it decides" title="Four tiers, cheapest first">
      <p className="max-w-2xl text-[15px] leading-relaxed text-stone-600">
        Identity is not settled by one clever model. It runs down a cascade, and every decision
        records which tier made it. Most pairs are resolved by facts that cost nothing to check,
        which is what makes the approach affordable at the scale of a real material master.
      </p>

      <div className="mt-9 rounded-2xl border border-stone-200 bg-white p-6 sm:p-8">
        <CascadeBar />
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <Note>
          Measured over a 3,210-pair rebuild, not projected. Of the 176 pairs the model did see,
          it called 129 the same material, 29 different, and abstained on 18.
        </Note>
        <Note>
          The cheap tiers carrying 94.5% is also the sovereignty answer: the model tier is an
          enhancement to the ambiguous remainder, not the engine. The whole system runs on
          premises.
        </Note>
      </div>
    </Section>
  )
}

function Verdicts() {
  const tones: Record<string, string> = {
    brand: 'border-brand-300 bg-brand-50',
    stone: 'border-stone-200 bg-stone-50',
    khaki: 'border-khaki-300 bg-khaki-50',
    primary: 'border-primary-300 bg-primary-50 ring-1 ring-primary-300',
  }
  return (
    <Section id="verdicts" n="03" kicker="Refusal as an output" title="Four answers, not two" panel>
      <p className="max-w-2xl text-[15px] leading-relaxed text-stone-600">
        A similarity score has to say yes or no. It cannot represent a fact being{' '}
        <em className="not-italic font-medium text-stone-900">absent</em>. That is the single
        difference that matters most, because in a refinery a wrong merge is a safety incident,
        not a data-quality ticket.
      </p>

      {/* The mark sits on the crossing of the four cards, so the verdicts read as four outputs of
          one thing. The gap at this breakpoint is set to twice the badge's overhang, which keeps
          it clear of every card's own padding and off the titles in the bottom row. */}
      <div className="relative mt-9">
        <div className="grid gap-4 sm:grid-cols-2 sm:gap-6">
          {VERDICTS.map((v) => (
            <div key={v.verdict} className={`rounded-2xl border p-5 ${tones[v.tone]}`}>
              <p className="font-display text-2xl tracking-tight text-stone-900">{v.verdict}</p>
              <p className="mt-2 text-sm leading-relaxed text-stone-600">{v.body}</p>
            </div>
          ))}
        </div>

        <span className="pointer-events-none absolute top-1/2 left-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-stone-200 bg-white p-1 shadow-[0_10px_30px_-12px_rgba(28,25,23,0.4)] sm:flex">
          <img src="/logo.png" alt="Meridian" className="h-14 w-14 object-contain" />
        </span>
      </div>

      <div className="mt-6 rounded-2xl border border-stone-200 bg-stone-50 p-6">
        <p className="text-[15px] leading-relaxed text-stone-700">
          On the benchmark catalogue Meridian declined{' '}
          <strong className="font-mono font-semibold text-stone-900">3,010</strong> pairs — 21.8%
          — and routed each one to the steward who could answer it.{' '}
          <span className="text-stone-500">
            No baseline in the comparison below abstains on a single pair, because none of them can.
          </span>
        </p>
      </div>
    </Section>
  )
}

function Gates() {
  return (
    <Section id="gates" n="04" kicker="Safety" title="The rules sit outside the model">
      <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
        <div>
          <p className="text-[15px] leading-relaxed text-stone-600">
            Conflict gates are deterministic, declared as data, and able to veto the model
            outright. If two bolts carry different strength grades they are different parts, and
            no amount of confidence changes that.
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-stone-600">
            This is also what makes the system arguable. A plant engineer who disagrees with a
            rule can open the file, read it in plain YAML, and say so — without anyone retraining
            anything.
          </p>
          <ul className="mt-6 space-y-2.5">
            {[
              'Families, attributes, units, gates and blocking are data, not code',
              'Canonical IDs come from a registry, never from a language model',
              'Decisions are append-only; the trail cannot be quietly rewritten',
              'Extraction may output "unknown" — a missing critical attribute is why the system asks',
            ].map((rule) => (
              <li key={rule} className="flex gap-3 text-sm text-stone-600">
                <svg viewBox="0 0 24 24" fill="none" stroke="#2fb85e" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 h-4 w-4 shrink-0">
                  <path d="m5 13 4 4L19 7" />
                </svg>
                {rule}
              </li>
            ))}
          </ul>
        </div>

        <GateVeto />
      </div>
    </Section>
  )
}

function Evidence() {
  return (
    <section id="evidence" className="evidence-surface relative scroll-mt-4 overflow-hidden text-stone-200">
      <div className="line-hatch hatch-tr pointer-events-none absolute inset-0" />
      <div className="line-hatch hatch-bl pointer-events-none absolute inset-0" />
      <FloatingParts />
      <div className="relative mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:py-24">
        <Eyebrow dark>05 — Evidence</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-display text-4xl leading-[1.08] tracking-tight text-white sm:text-5xl">
          Measured against every obvious alternative
        </h2>
        <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-stone-400">
          The honest test is not whether a matcher finds true pairs. It is what it does with{' '}
          <strong className="font-medium text-stone-200">hard negatives</strong> — pairs built to
          look alike and not be alike, which is exactly what a material master is full of. Every
          baseline below was given the same blocking and its best possible threshold, chosen with
          the answers in hand.
        </p>

        <div className="mt-12 grid gap-12 lg:grid-cols-[1.25fr_1fr] lg:gap-16">
          <div>
            <p className="mb-6 text-xs font-semibold tracking-[0.14em] text-stone-500 uppercase">
              Wrongly merged share of hard negatives · lower is better
            </p>
            <BaselineBars />
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <p className="font-display text-5xl tracking-tight text-brand-500">99.3%</p>
              <p className="mt-2 text-sm text-stone-300">
                pairwise precision — 13 wrong merges across 1,772 merges made
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <p className="mb-5 text-xs font-semibold tracking-[0.14em] text-stone-500 uppercase">
                Why this stays affordable
              </p>
              <RetrievalFunnel />
              <p className="mt-5 text-xs leading-relaxed text-stone-500">
                Blocking removes 99.48% of comparisons on the 18,611-record catalogue and loses
                nothing. The heavy pass happens once; after that each new part is checked as it is
                created, which is almost free.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 rounded-2xl border border-white/10 bg-white/5 p-6 sm:p-8">
          <p className="text-[15px] leading-relaxed text-stone-300">
            The row worth reading twice is the model on raw text. It is far better than string
            similarity and still merges{' '}
            <strong className="font-mono font-semibold text-white">528</strong> pairs that are not
            the same part — and it needs one model call for every pair it judges, where Meridian
            reached a model on{' '}
            <strong className="font-mono font-semibold text-white">0.0%</strong> of pairs in that
            run. The deterministic tiers settled every one of them.
          </p>
        </div>
      </div>
    </section>
  )
}

function Additive() {
  return (
    <Section id="additive" n="06" kicker="Additive by design" title="Nothing is deleted, merged or overwritten">
      <div className="grid gap-8 lg:grid-cols-[1fr_1.15fr] lg:gap-14">
        <div>
          <p className="text-[15px] leading-relaxed text-stone-600">
            Every vendor in this market cleans a customer's master by deleting and merging records
            inside their system. That is permanent, it is why these projects frighten plant teams,
            and it is why they stall for years.
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-stone-600">
            Meridian only ever <strong className="font-semibold text-stone-900">adds a row</strong>{' '}
            saying two things are the same part. Every CPSE keeps its code exactly as it was. If a
            link is wrong, the link is deleted and nothing is lost.
          </p>

          <div className="mt-7 rounded-2xl border border-stone-200 bg-white p-5">
            <p className="mb-3 text-xs font-semibold tracking-wide text-stone-400 uppercase">Retained, untouched</p>
            <div className="flex flex-wrap gap-2">
              {['BP-4471-M16', 'CP-MAT-88210', 'IO-31-004417', 'NT-HB-16080'].map((c) => (
                <span key={c} className="rounded-lg bg-stone-100 px-2.5 py-1.5 font-mono text-xs text-stone-600">
                  {c}
                </span>
              ))}
            </div>
            <div className="my-4 h-px bg-stone-100" />
            <p className="mb-3 text-xs font-semibold tracking-wide text-brand-700 uppercase">Added</p>
            <span className="inline-block rounded-lg bg-brand-900 px-3 py-2 font-mono text-sm font-semibold text-brand-100">
              IN-31161600-0000417-3
            </span>
          </div>
        </div>

        <div>
          <p className="mb-6 text-[15px] leading-relaxed text-stone-600">
            The national code follows the precedent India already participates in — the NATO
            Codification System, which India joined in 2008 as a Tier-1 member. The rule that
            matters: the identification number never changes, even when the item is reclassified.
          </p>
          <NationalCodeAnatomy />
          <div className="mt-8">
            <Note>
              Reclassification changes the printed code and never the identity, so a code printed
              on a bin label and quoted in a purchase order stays valid. The check digit rejects a
              mistyped code instead of letting it resolve to nothing.
            </Note>
          </div>
        </div>
      </div>
    </Section>
  )
}

function Impact() {
  return (
    <section id="impact" className="scroll-mt-4 border-y border-stone-900/5 bg-white">
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
        <Eyebrow>07 — Impact</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-display text-4xl leading-[1.08] tracking-tight sm:text-5xl">
          What one national code is actually worth
        </h2>
        <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-stone-600">
          Computed from 1,418 purchase order lines across four CPSEs and four years — ₹29.0 crore
          of real analysed spend — rather than from a price column taken on trust.
        </p>

        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-brand-300 bg-brand-50 p-6">
            <p className="font-display text-4xl tracking-tight text-brand-900">₹3.91 cr</p>
            <p className="mt-2 text-sm font-medium text-stone-700">demand aggregation opportunity</p>
            <p className="mt-1 text-xs leading-snug text-stone-500">
              19.3% of ₹20.3 crore of spend on materials that more than one CPSE buys — invisible
              until the codes are linked.
            </p>
          </div>

          <div className="rounded-2xl border border-primary-300 bg-primary-50 p-6">
            <p className="font-display text-4xl tracking-tight text-primary-700">₹20.2 lakh</p>
            <p className="mt-2 text-sm font-medium text-stone-700">purchasing avoidable by transfer</p>
            <p className="mt-1 text-xs leading-snug text-stone-500">
              30 opportunities, 17,386 base units sitting in one CPSE's store that another is
              about to order.
            </p>
          </div>

          <div className="rounded-2xl border border-stone-300 bg-stone-50 p-6">
            <p className="font-display text-4xl tracking-tight text-stone-900">₹78.6 lakh</p>
            <p className="mt-2 text-sm font-medium text-stone-700">deliberately not claimed</p>
            <p className="mt-1 text-xs leading-snug text-stone-500">
              Savings from six clusters our own audit check flagged as possible false merges,
              excluded and reported separately.
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto rounded-2xl border border-stone-200 bg-brand-900 p-6 sm:p-7">
          <p className="mb-4 text-xs font-semibold tracking-[0.14em] text-stone-500 uppercase">
            One redistribution finding, in full
          </p>
          <pre className="font-mono text-[12.5px] leading-relaxed text-stone-300 sm:text-[13px]">
            <span className="text-brand-500">IN-31161600-0000011-4</span>{'   '}BOLT, HEX HEAD; M10X80; A2-70; DIN931{'\n'}
            {'  '}<span className="text-stone-500">HOLDS</span>{'  '}CPCL: 20 BOX-100 = 2,000 each, unissued 1,732 days{'\n'}
            {'  '}<span className="text-stone-500">BUYS</span>{'   '}BPCL: 1,107/yr at ₹218.84/each, 6 orders{'\n'}
            {'  '}<span className="text-brand-500">→ transfer 1,107, avoid ₹2,42,225</span>
          </pre>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-stone-400">
            Twenty boxes against two thousand each: unit normalisation is the difference between a
            transfer recommendation and a nonsense one. The finding names both parties and ends in
            an action rather than an observation — and it is impossible without cross-organisation
            identity.
          </p>
        </div>

        <div className="mt-4 rounded-2xl border border-stone-200 bg-[#fbfaf7] p-6">
          <p className="text-[15px] leading-relaxed text-stone-700">
            <strong className="font-semibold text-stone-900">
              Refusing to claim ₹78.6 lakh is the point, not a footnote.
            </strong>{' '}
            The top savings cluster was one of our own false merges — two different materials
            priced differently, which is an error wearing a suit. Price variance turned out to
            detect exactly that, and the flagged clusters are now excluded from every figure above.
          </p>
        </div>
      </div>
    </section>
  )
}

function Close() {
  return (
    <section className="relative overflow-hidden">
      <div className="app-canvas absolute inset-0" />

      {/* The name sunk into the bottom edge — pushed down far enough that the section's own
          overflow cuts the lower half of the letterforms off, so it reads as buried rather than
          as a caption that happens to be large. The section's bottom padding is sized to clear
          the part that stays visible. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center overflow-hidden">
        <span className="translate-y-[46%] font-sans text-[15vw] leading-none font-extrabold tracking-[0.03em] whitespace-nowrap text-brand-900/8 select-none">
          MERIDIAN
        </span>
      </div>

      <div className="relative mx-auto max-w-3xl px-5 pt-20 pb-36 text-center sm:px-8 lg:pt-28 lg:pb-44">
        <img src="/logo.png" alt="" className="mx-auto h-28 w-28 object-contain sm:h-32 sm:w-32" />
        <h2 className="mt-6 font-display text-4xl leading-[1.08] tracking-tight sm:text-5xl">
          Four organisations keep everything.
          <br />
          <span className="text-brand-700">The country gets one code.</span>
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-[15px] leading-relaxed text-stone-600">
          Nobody surrenders their ERP, their codes or their data. The whole system runs inside your
          own building, and 94.5% of what it decides never reaches a model at all.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            to="/login"
            className="rounded-xl bg-brand-900 px-6 py-3 text-sm font-medium text-brand-100 shadow-sm transition-colors hover:bg-stone-900"
          >
            Enter the platform
          </Link>
          <a
            href="#top"
            className="rounded-xl border border-stone-300 bg-white/70 px-6 py-3 text-sm font-medium text-stone-700 transition-colors hover:border-stone-400 hover:bg-white"
          >
            Back to the top
          </a>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-stone-900/5 bg-[#fbfaf7]">
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-2.5">
            <img src="/logo.png" alt="" className="h-8 w-8 object-contain" />
            <span className="font-display text-lg tracking-tight">Meridian</span>
          </div>
          <p className="max-w-2xl text-xs leading-relaxed text-stone-500">
            <strong className="font-semibold text-stone-700">Simulated data.</strong> Every figure
            on this page is measured over a deterministically generated four-CPSE catalogue with
            held-out ground truth, not over any organisation's real material master. Organisation
            names denote simulated catalogues modelled on public-sector enterprises. The ₹12,743
            crore figure is from CAG Report No. 10 of 2025 and is cited, not produced by this
            system.
          </p>
        </div>
      </div>
    </footer>
  )
}

/** `panel` lifts a section onto a white band with hairline rules. Used to alternate against the
 *  page's warm ground so consecutive sections do not run together, without introducing another
 *  colour into the page. */
function Section({
  id,
  n,
  kicker,
  title,
  children,
  panel,
}: {
  id: string
  n: string
  kicker: string
  title: string
  children: ReactNode
  panel?: boolean
}) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 ${panel ? 'border-y border-stone-900/8 bg-white' : ''}`}
    >
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
        <Eyebrow>
          {n} — {kicker}
        </Eyebrow>
        <h2 className="mt-4 mb-6 max-w-3xl font-display text-4xl leading-[1.08] tracking-tight sm:text-5xl">
          {title}
        </h2>
        {children}
      </div>
    </section>
  )
}

/** Rupee marks drifting behind the cost section. Positions are hand-placed to stay out of the
 *  headline figure's way, and the durations are deliberately co-prime-ish so the set never
 *  visibly loops as a group. */
const RUPEES = [
  { left: '3%', top: '14%', size: 68, o: 0.26, dur: '11s', delay: '0s', tilt: -10 },
  { left: '15%', top: '72%', size: 40, o: 0.24, dur: '9s', delay: '1.4s', tilt: 7 },
  { left: '27%', top: '26%', size: 26, o: 0.2, dur: '13s', delay: '0.6s', tilt: -4 },
  { left: '38%', top: '86%', size: 52, o: 0.22, dur: '10s', delay: '2.2s', tilt: 12 },
  { left: '55%', top: '6%', size: 34, o: 0.24, dur: '12s', delay: '0.9s', tilt: -7 },
  { left: '69%', top: '58%', size: 30, o: 0.19, dur: '14s', delay: '3s', tilt: 5 },
  { left: '82%', top: '18%', size: 58, o: 0.26, dur: '10.5s', delay: '1.8s', tilt: 9 },
  { left: '92%', top: '74%', size: 44, o: 0.24, dur: '12.5s', delay: '0.3s', tilt: -12 },
  { left: '47%', top: '44%', size: 22, o: 0.17, dur: '15s', delay: '2.6s', tilt: 3 },
]

function FloatingRupees() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {RUPEES.map((r) => (
        <span
          key={`${r.left}-${r.top}`}
          className="soft-float absolute font-display leading-none text-primary-700 select-none"
          style={
            {
              left: r.left,
              top: r.top,
              fontSize: `${r.size}px`,
              opacity: r.o,
              '--dur': r.dur,
              '--delay': r.delay,
              '--tilt': `${r.tilt}deg`,
            } as CSSProperties
          }
        >
          ₹
        </span>
      ))}
    </div>
  )
}

/** The parts themselves, drifting behind the evidence — the things actually being matched. Kept
 *  to the outer margins, which on a wide screen fall outside the content column entirely. */
const FLOATING_PARTS = [
  { Part: HexBolt, left: '2%', top: '14%', size: 104, o: 0.12, dur: '13s', delay: '0s', tilt: -14 },
  { Part: BallValve, left: '86%', top: '9%', size: 92, o: 0.1, dur: '18s', delay: '2.6s', tilt: 9 },
  { Part: SpiralGasket, left: '7%', top: '74%', size: 84, o: 0.1, dur: '15s', delay: '1.2s', tilt: 7 },
  { Part: BallBearing, left: '90%', top: '70%', size: 116, o: 0.11, dur: '16s', delay: '3.4s', tilt: -6 },
]

function FloatingParts() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 hidden overflow-hidden lg:block">
      {FLOATING_PARTS.map(({ Part, left, top, size, o, dur, delay, tilt }) => (
        <span
          key={left + top}
          className="soft-float absolute block text-brand-100"
          style={
            {
              left,
              top,
              opacity: o,
              '--dur': dur,
              '--delay': delay,
              '--tilt': `${tilt}deg`,
            } as CSSProperties
          }
        >
          <Part className="block" style={{ width: size, height: size }} />
        </span>
      ))}
    </div>
  )
}

/** Dots falling from the section's top edge: at most three in any one column, and the number
 *  varies column to column. Deterministic rather than genuinely random — a hash of the column
 *  index — so the pattern is stable between renders instead of reshuffling on every paint. */
const FALL = Array.from({ length: 32 }, (_, i) => {
  const hash = Math.abs(Math.sin((i + 1) * 12.9898) * 43758.5453) % 1
  return 1 + Math.floor(hash * 3)
})

function FallingDots() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 top-0 flex justify-between px-3 sm:px-6"
    >
      {FALL.map((count, i) => (
        <span key={i} className="flex flex-col items-center gap-2.5 pt-3">
          {Array.from({ length: count }, (_, j) => (
            <span
              key={j}
              className="h-1.5 w-1.5 rounded-full bg-stone-900"
              style={{ opacity: 0.3 - j * 0.075 }}
            />
          ))}
        </span>
      ))}
    </div>
  )
}

/** An evenly spaced triangle of dots tucked into a card corner: five in the row along the edge,
 *  then four, three, two, one, so the block thins away toward the middle of the card. The same
 *  grid is reused rotated 180° for the opposite corner. */
const DOT_ROWS = [5, 4, 3, 2, 1]
const DOT_GAP = 18

const DOTS = DOT_ROWS.flatMap((count, row) =>
  Array.from({ length: count }, (_, i) => ({ x: 102 - i * DOT_GAP, y: 18 + row * DOT_GAP })),
)

// The grid is authored against the top-right corner; the other three are that same grid
// mirrored into place, so all four stay identical and correctly handed.
const CORNER_TRANSFORM = {
  tr: undefined,
  tl: 'scale(-1 1) translate(-120 0)',
  br: 'scale(1 -1) translate(0 -120)',
  bl: 'rotate(180 60 60)',
} as const

const CORNER_POSITION = {
  tr: 'top-0 right-0',
  tl: 'top-0 left-0',
  br: 'bottom-0 right-0',
  bl: 'bottom-0 left-0',
} as const

function CornerDots({ corner }: { corner: keyof typeof CORNER_TRANSFORM }) {
  return (
    <svg
      viewBox="0 0 120 120"
      aria-hidden="true"
      className={`pointer-events-none absolute h-32 w-32 sm:h-40 sm:w-40 lg:h-48 lg:w-48 ${CORNER_POSITION[corner]}`}
    >
      <g transform={CORNER_TRANSFORM[corner]} fill="#ffffff" opacity={0.5}>
        {DOTS.map((d) => (
          <circle key={`${d.x}-${d.y}`} cx={d.x} cy={d.y} r={3} />
        ))}
      </g>
    </svg>
  )
}

function Eyebrow({ children, dark }: { children: ReactNode; dark?: boolean }) {
  return (
    <p className={`text-xs font-semibold tracking-[0.14em] uppercase ${dark ? 'text-brand-500' : 'text-brand-700'}`}>
      {children}
    </p>
  )
}

function Note({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white/60 p-4">
      <p className="text-[13px] leading-relaxed text-stone-500">{children}</p>
    </div>
  )
}
