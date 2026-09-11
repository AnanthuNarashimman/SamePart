// The problem and the product in one object the reader operates themselves.
//
// The four sources are drawn as the things a material master actually lives in — a phosphor
// terminal, a manila file, a bound register, a card index — and each one carries its own record
// written inside it, not beside it. The divergence is therefore something you read off the
// objects rather than something the caption claims.
//
// All four feed one window. Switched off it shows what a CPSE can see today: four records, no
// links, and the audited cost of that blindness. Switched on, the same window becomes Meridian.
// Making it a switch rather than a static before-and-after is the point — the reader performs
// the change, so the difference is something they did.

type Source = {
  org: string
  code: string
  style: string
  text: string
  colour: string
}

const SOURCES: Source[] = [
  {
    org: 'BPCL',
    code: 'BP-4471-M16',
    style: 'Heavily abbreviated',
    text: 'BLT HEX HD M16X80MM SS304 A2-70',
    colour: '#2a78d6',
  },
  {
    org: 'CPCL',
    code: 'CP-MAT-88210',
    style: 'Terse capitals',
    text: 'HEX BOLT M16X80 A2-70 ISO 4014',
    colour: '#eb6834',
  },
  {
    org: 'IOCL',
    code: 'IO-31-004417',
    style: 'Verbose title case',
    text: 'Bolt, Hexagon Head, M16 x 80mm, Property Class A2-70',
    colour: '#1baf7a',
  },
  {
    org: 'NTPC',
    code: 'NT-HB-16080',
    style: 'Semicolon-delimited',
    text: 'BOLT HEX HEAD; DIA 16MM; LG 80MM; GRADE A2-70',
    colour: '#eda100',
  },
]

const TRACKS = [125, 375, 625, 875]

// Four objects of genuinely different shapes still have to sit on one line, so each is built
// inside the same envelope: a fixed strip at the top the width of the folder's tab, a body that
// stretches to fill, and a fixed strip at the bottom the height of the terminal's stand. Objects
// without a tab or a stand simply leave their strip empty, which puts every record block and
// every base at the same height across the row.
const TOP_STRIP = 'h-3'
const BASE_STRIP = 'h-4'

/** The record area stretches to fill its object, so descriptions of different lengths do not
 *  give the four objects different heights. */
const BODY = 'flex-1 min-h-[76px] sm:min-h-[84px]'

/** Controlled, because the section above owns the switch: it is thrown by scrolling the stage
 *  through its locked view, and by the toggle in the window's own title bar. */
export function ProblemStage({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-3">
        <Terminal s={SOURCES[0]} />
        <FolderSheet s={SOURCES[1]} />
        <LedgerPage s={SOURCES[2]} />
        <IndexCard s={SOURCES[3]} />
      </div>

      {/* Cables. The four origins sit at the column centres of a four-track grid, so they stay
          aligned with the objects at any width; below that breakpoint they become one arrow.
          They carry each organisation's colour and a travelling pulse only while the system is
          on — dead cable, dead system. */}
      <svg viewBox="0 0 1000 96" preserveAspectRatio="none" aria-hidden="true" className="hidden h-12 w-full lg:block">
        {TRACKS.map((x, i) => {
          const d = `M ${x} 0 C ${x} 54, 500 40, 500 96`
          return (
            <g key={x}>
              <path
                d={d}
                fill="none"
                stroke={on ? SOURCES[i].colour : '#d6d3d1'}
                strokeWidth={1.4}
                vectorEffect="non-scaling-stroke"
                opacity={on ? 0.45 : 1}
                className="transition-[stroke] duration-500"
              />
              {on && (
                <path
                  className="mrd-flow"
                  d={d}
                  pathLength={100}
                  fill="none"
                  stroke={SOURCES[i].colour}
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  style={{ animationDelay: `${i * 0.4}s` }}
                />
              )}
            </g>
          )
        })}
      </svg>

      <div className="flex justify-center py-5 lg:hidden">
        <svg viewBox="0 0 24 24" fill="none" stroke="#a8a29e" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
          <path d="M12 4v16m0 0 6-6m-6 6-6-6" />
        </svg>
      </div>

      <Window on={on} onToggle={onToggle} />

      <p className="mt-4 text-center text-xs text-stone-400">
        {on
          ? 'Every source code is still there, untouched. Switch it off to see today.'
          : 'Keep scrolling, or use the switch in the window, to turn Meridian on.'}
      </p>
    </div>
  )
}

/* ---------------------------------------------------------------- the four sources */

function Caption({ s }: { s: Source }) {
  return (
    <p className="mt-2 text-center text-[10px] text-stone-400">
      <span className="font-mono font-semibold text-stone-600">{s.org}</span> · {s.style}
    </p>
  )
}

/** A phosphor terminal, record shown on the screen itself. */
function Terminal({ s }: { s: Source }) {
  return (
    <div className="flex h-full flex-col">
      <div className={TOP_STRIP} />
      <div className="flex flex-1 flex-col rounded-xl bg-gradient-to-b from-stone-300 to-stone-400 p-2 shadow-sm ring-1 ring-stone-400/50">
        <div className={`crt-lines relative overflow-hidden rounded-md bg-[#06120b] p-2.5 ${BODY}`}>
          <p className="font-mono text-[9px] text-emerald-500/80">&gt; {s.code}</p>
          <p className="mt-1.5 font-mono text-[10px] leading-relaxed break-words text-emerald-300">
            {s.text}
          </p>
        </div>
        <div className="flex items-center justify-between px-1 pt-1.5">
          <span className="font-mono text-[8px] tracking-widest text-stone-600 uppercase">terminal</span>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        </div>
      </div>
      <div className={`flex flex-col items-center ${BASE_STRIP}`}>
        <span className="h-2.5 w-9 bg-stone-400" />
        <span className="h-1.5 w-16 rounded-b-md bg-stone-400" />
      </div>
      <Caption s={s} />
    </div>
  )
}

/** A manila file with a typed sheet in it. */
function FolderSheet({ s }: { s: Source }) {
  return (
    <div className="flex h-full flex-col">
      <div className={TOP_STRIP}>
        <span className="ml-3 block h-full w-16 rounded-t-md bg-[#e7cb94]" />
      </div>
      <div className="flex flex-1 flex-col rounded-lg rounded-tl-none bg-gradient-to-b from-[#e7cb94] to-[#d9b46f] p-2 shadow-sm ring-1 ring-[#c9a25c]/60">
        <div className={`-rotate-[1.2deg] rounded-sm bg-white p-2.5 shadow-sm ring-1 ring-black/5 ${BODY}`}>
          <p className="font-mono text-[9px] text-stone-400">{s.code}</p>
          <p className="mt-1.5 font-mono text-[10px] leading-relaxed break-words text-stone-700">
            {s.text}
          </p>
        </div>
        <p className="pt-1.5 text-center font-mono text-[8px] tracking-widest text-[#7d5f22] uppercase">
          file copy
        </p>
      </div>
      <div className={BASE_STRIP} />
      <Caption s={s} />
    </div>
  )
}

/** A bound register, record written on the ruled page. */
function LedgerPage({ s }: { s: Source }) {
  return (
    <div className="flex h-full flex-col">
      <div className={TOP_STRIP} />
      <div className="flex flex-1 flex-col rounded-lg bg-gradient-to-b from-[#8d6a4f] to-[#71533c] p-2 shadow-sm ring-1 ring-[#5c412e]/50">
        <div className={`ruled-blue relative overflow-hidden rounded-sm bg-[#fdfaef] py-2.5 pr-2.5 pl-6 ring-1 ring-[#e3d9bf] ${BODY}`}>
          <span className="absolute inset-y-0 left-4 w-px bg-rose-300" />
          <p className="font-mono text-[9px] text-stone-400">{s.code}</p>
          <p className="mt-1.5 font-mono text-[10px] leading-relaxed break-words text-stone-700">
            {s.text}
          </p>
        </div>
        <p className="pt-1.5 text-center font-mono text-[8px] tracking-widest text-[#e3d0bc] uppercase">
          register
        </p>
      </div>
      <div className={BASE_STRIP} />
      <Caption s={s} />
    </div>
  )
}

/** A card from a card index, colour-banded and punched. */
function IndexCard({ s }: { s: Source }) {
  return (
    <div className="flex h-full flex-col">
      <div className={TOP_STRIP} />
      <div className="flex flex-1 flex-col overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-stone-300">
        <div className="h-2 shrink-0" style={{ backgroundColor: s.colour }} />
        <div className={`ruled-blue px-2.5 pt-2.5 pb-1 ${BODY}`}>
          <p className="font-mono text-[9px] text-stone-400">{s.code}</p>
          <p className="mt-1.5 font-mono text-[10px] leading-relaxed break-words text-stone-700">
            {s.text}
          </p>
        </div>
        <div className="flex items-center justify-center gap-1.5 border-t border-stone-200 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full ring-1 ring-stone-300" />
          <span className="font-mono text-[8px] tracking-widest text-stone-400 uppercase">card index</span>
        </div>
      </div>
      <div className={BASE_STRIP} />
      <Caption s={s} />
    </div>
  )
}

/* ---------------------------------------------------------------- the window */

function Window({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <div className="mx-auto max-w-xl overflow-hidden rounded-xl border border-stone-300 shadow-[0_26px_60px_-32px_rgba(28,25,23,0.55)]">
      {/* Window chrome stays light in both states, so the switch reads as one machine changing
          what it runs rather than as two different screenshots. */}
      <div className="flex items-center justify-between gap-3 border-b border-stone-200 bg-stone-100 px-3 py-2">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={on}
          onClick={onToggle}
          className="group flex items-center gap-2"
        >
          <span
            className={`text-[10px] font-semibold tracking-wide transition-colors ${
              on ? 'text-brand-700' : 'text-stone-500 group-hover:text-stone-700'
            }`}
          >
            Meridian
          </span>
          <span
            className={`relative h-[18px] w-8 rounded-full transition-colors ${
              on ? 'bg-brand-600' : 'bg-stone-300 group-hover:bg-stone-400'
            }`}
          >
            <span
              className={`absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white shadow transition-[left] duration-300 ${
                on ? 'left-[16px]' : 'left-[2px]'
              }`}
            />
          </span>
        </button>
      </div>

      <div className="relative aspect-[16/10]">
        <TodayScreen on={on} />
        <MeridianScreen on={on} />
      </div>
    </div>
  )
}

function TodayScreen({ on }: { on: boolean }) {
  return (
    <div
      className={`absolute inset-0 flex flex-col justify-between bg-[#0a0d0b] p-3 transition-opacity duration-500 sm:p-5 ${
        on ? 'pointer-events-none opacity-0' : 'opacity-100'
      }`}
    >
      <div className="flex items-center gap-2 border-b border-white/10 pb-2">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-rose-500" />
        <span className="font-mono text-[9px] tracking-[0.16em] text-rose-400 uppercase sm:text-[10px]">
          No cross-organisation view
        </span>
      </div>

      <div className="space-y-1 sm:space-y-1.5">
        {SOURCES.map((s) => (
          <div
            key={s.org}
            className="flex items-center gap-2 rounded border border-white/6 bg-white/[0.03] px-2 py-1 sm:px-2.5 sm:py-1.5"
          >
            <span className="w-9 shrink-0 font-mono text-[9px] text-stone-400 sm:text-[10px]">{s.org}</span>
            <span className="flex-1 truncate font-mono text-[9px] text-stone-500 sm:text-[10px]">{s.code}</span>
            <span className="shrink-0 font-mono text-[9px] text-rose-400/90 sm:text-[10px]">no match</span>
          </div>
        ))}
      </div>

      <div className="border-t border-white/10 pt-2">
        <p className="font-mono text-[9px] text-stone-500 sm:text-[10px]">
          4 records · 0 links · duplicate buying invisible
        </p>
        <p className="mt-1 font-mono text-[11px] text-rose-400 sm:text-sm">
          ₹12,743 cr lost over seven years
        </p>
      </div>
    </div>
  )
}

function MeridianScreen({ on }: { on: boolean }) {
  return (
    <div
      className={`absolute inset-0 flex flex-col justify-between bg-[#fbfaf7] p-3 transition-opacity duration-500 sm:p-5 ${
        on ? 'opacity-100' : 'pointer-events-none opacity-0'
      }`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-stone-200 pb-2">
        <div className="flex items-center gap-1.5">
          <img src="/logo.png" alt="" className="h-4 w-4 object-contain sm:h-5 sm:w-5" />
          <span className="font-display text-xs text-stone-900 sm:text-sm">Meridian</span>
        </div>
        <span className="rounded-full bg-brand-100 px-2 py-0.5 font-mono text-[8px] font-semibold tracking-[0.1em] text-brand-900 uppercase sm:text-[9px]">
          identity confirmed
        </span>
      </div>

      <div className="rounded-lg bg-brand-900 px-2 py-1.5 text-center sm:py-2">
        <span className="font-mono text-[11px] font-semibold tracking-wide text-brand-100 sm:text-sm">
          IN-31161600-0000417-3
        </span>
      </div>

      <div className="space-y-1">
        {SOURCES.map((s) => (
          <div
            key={s.org}
            className="flex items-center gap-2 rounded border border-stone-200 bg-white px-2 py-1 sm:px-2.5"
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: s.colour }} />
            <span className="w-9 shrink-0 font-mono text-[9px] font-medium text-stone-700 sm:text-[10px]">
              {s.org}
            </span>
            <span className="flex-1 truncate font-mono text-[9px] text-stone-400 sm:text-[10px]">{s.code}</span>
            <span className="shrink-0 font-mono text-[9px] font-medium text-brand-700 sm:text-[10px]">
              linked
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-stone-200 pt-2">
        {[
          ['₹3.91 cr', 'aggregation'],
          ['₹20.2 L', 'stock transfer'],
          ['0', 'codes overwritten'],
        ].map(([value, label]) => (
          <div key={label}>
            <p className="font-display text-xs leading-none text-brand-900 sm:text-base">{value}</p>
            <p className="mt-1 font-mono text-[8px] text-stone-500 sm:text-[9px]">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
