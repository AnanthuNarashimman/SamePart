import type { ReactNode } from 'react'
import { HexBolt, HexBoltFace } from './parts'

// The pitch as a picture: one part, held under a different code by every organisation that
// stocks it, converging on one.
//
// Every tile is the same bolt seen from a different angle — three rotations of the side
// elevation and one view straight down the axis. That is the argument, not decoration: nothing
// about the item differs, only the vantage each organisation happened to write it down from.
//
// The tiles are laid out in HTML rather than inside the SVG so the text stays crisp and the
// grid can reflow on a phone. The converging lines are a separate SVG stretched with
// `preserveAspectRatio="none"`, and its four origins sit at 12.5 / 37.5 / 62.5 / 87.5% of the
// viewBox — exactly the column centres of a four-track grid, so they stay aligned at any width.
// Below that breakpoint the grid becomes two columns, the lines would no longer line up with
// anything, and they are replaced by a single arrow.

// Identity colours from the app's validated dark set, since these sit on the deep pine card
// rather than on white — all four clear 3:1 against a charcoal ground.
const SOURCES: { org: string; code: string; colour: string; art: ReactNode }[] = [
  { org: 'BPCL', code: 'BP-4471-M16', colour: '#3987e5', art: <HexBolt className="h-8 w-8" rotate={-34} /> },
  { org: 'CPCL', code: 'CP-MAT-88210', colour: '#e8703c', art: <HexBoltFace className="h-8 w-8" /> },
  { org: 'IOCL', code: 'IO-31-004417', colour: '#24b985', art: <HexBolt className="h-8 w-8" rotate={16} /> },
  { org: 'NTPC', code: 'NT-HB-16080', colour: '#e0a119', art: <HexBolt className="h-8 w-8" rotate={180} /> },
]

const TRACKS = [125, 375, 625, 875]

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

/**
 * `assembled` runs 0 → 1 as the hero's opening resolves into its resting layout, and
 * `captionOpacity` holds the caption back while it does — on first load the illustration is
 * meant to stand alone, with no prose anywhere on the screen.
 *
 * At 0 the convergence point is the Meridian mark, which is what the opening is about. At 1 the
 * mark has given way to the small node the resting layout uses. They cross-fade in a box whose
 * height interpolates between the two, so the code below slides up with them rather than
 * jumping when one is swapped for the other.
 */
export function ConvergenceHero({
  captionOpacity = 1,
  assembled = 1,
}: {
  captionOpacity?: number
  assembled?: number
}) {
  return (
    <div className="mx-auto w-full max-w-2xl">
      {/* The tiles stand further apart while the opening holds them on their own, and close up
          as the hero assembles around them. Scaling the whole illustration alone would have kept
          the gaps in proportion to the tiles, which is exactly what made the opening feel
          cramped: four large objects with the spacing of four small ones. */}
      <div
        className="grid grid-cols-2 sm:grid-cols-4"
        style={{ gap: `${lerp(18, 11, assembled)}px` }}
      >
        {SOURCES.map((s) => (
          <div
            key={s.org}
            className="flex flex-col items-center rounded-xl border border-white/15 bg-white/10 px-2.5 py-3 backdrop-blur-sm"
          >
            <span style={{ color: s.colour }}>{s.art}</span>
            <span className="mt-2 font-mono text-[10px] font-semibold tracking-wide text-white">
              {s.org}
            </span>
            <span className="mt-0.5 font-mono text-[9px] text-stone-300">{s.code}</span>
          </div>
        ))}
      </div>

      <svg
        viewBox="0 0 1000 96"
        preserveAspectRatio="none"
        aria-hidden="true"
        className="hidden h-9 w-full sm:block"
        style={{ marginTop: `${lerp(8, 0, assembled)}px` }}
      >
        {TRACKS.map((x, i) => {
          const d = `M ${x} 0 C ${x} 52, 500 42, 500 96`
          return (
            <g key={x}>
              <path d={d} fill="none" stroke="#ffffff" strokeWidth={1} vectorEffect="non-scaling-stroke" opacity={0.16} />
              <path
                className="mrd-flow"
                d={d}
                pathLength={100}
                fill="none"
                stroke={SOURCES[i].colour}
                strokeWidth={1.8}
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
                style={{ animationDelay: `${i * 0.42}s` }}
              />
            </g>
          )
        })}
      </svg>

      <div className="flex justify-center py-2 sm:hidden">
        <svg viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" opacity={0.4} className="h-5 w-5">
          <path d="M12 4v16m0 0 6-6m-6 6-6-6" />
        </svg>
      </div>

      {/* The lines converge into the mark and one code comes out the other side. */}
      <div className="flex flex-col items-center">
        <div
          className="relative flex items-center justify-center"
          style={{ height: `${lerp(56, 6, assembled)}px` }}
        >
          <span
            className="absolute flex h-14 w-14 items-center justify-center rounded-full border border-white/15 bg-white/10 shadow-[0_0_20px_-10px_rgba(114,242,148,0.35)] backdrop-blur-sm"
            style={{ opacity: 1 - assembled, transform: `scale(${lerp(1, 0.3, assembled)})` }}
          >
            <img src="/logo.png" alt="Meridian" className="h-10 w-10 object-contain" />
          </span>
          <span
            className="absolute h-1.5 w-1.5 rounded-full bg-brand-500"
            style={{ opacity: assembled }}
          />
        </div>
        <span
          className="w-px bg-gradient-to-b from-white/25 to-brand-500"
          style={{ height: `${lerp(16, 8, assembled)}px`, opacity: 1 - assembled }}
        />
        <div className="rounded-lg bg-brand-500 px-3.5 py-2.5 shadow-[0_6px_18px_-14px_rgba(114,242,148,0.45)]">
          <span className="font-mono text-xs font-semibold tracking-wide text-brand-900 sm:text-sm">
            IN-31161600-0000417-3
          </span>
        </div>
        <p className="mt-2.5 text-xs text-stone-400" style={{ opacity: captionOpacity }}>
          One national code. Every source code kept.
        </p>
      </div>
    </div>
  )
}
