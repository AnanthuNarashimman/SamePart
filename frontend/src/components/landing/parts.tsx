// The four material families the dictionaries actually declare, drawn rather than photographed.
//
// Line art on a 64-unit grid, stroked with currentColor at a uniform weight, so a part can be
// tinted to an organisation's identity colour and sit beside the app's own icon set without
// looking imported from somewhere else.

import type { CSSProperties } from 'react'

type PartProps = { className?: string; style?: CSSProperties }

const base = {
  viewBox: '0 0 64 64',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

/** Hex bolt, side elevation: chamfered head, plain shank, threaded run. `rotate` turns the
 *  whole part about the centre of the grid — the drawing stays inside the 64-unit box at any
 *  angle, since its half-diagonal is 29.4. */
export function HexBolt({ className, style, rotate = 0 }: PartProps & { rotate?: number }) {
  return (
    <svg {...base} className={className} style={style} aria-hidden="true">
      <g transform={rotate ? `rotate(${rotate} 32 32)` : undefined}>
        <path d="M7 24.5 14.5 17h11v30h-11L7 39.5z" />
        <path d="M25.5 25.5h32v13h-32z" />
        <path d="M33 25.5v13M38.5 25.5v13M44 25.5v13M49.5 25.5v13M55 25.5v13" />
        <path d="M14.5 17v30" opacity={0.45} />
      </g>
    </svg>
  )
}

/** The same bolt seen down its own axis: hex flats, the chamfer, and the shank end-on. */
export function HexBoltFace({ className, style }: PartProps) {
  return (
    <svg {...base} className={className} style={style} aria-hidden="true">
      <path d="M56 32 44 52.78 20 52.78 8 32 20 11.22 44 11.22Z" />
      <path d="M50 32 41 47.59 23 47.59 14 32 23 16.41 41 16.41Z" opacity={0.5} />
      <circle cx={32} cy={32} r={9} />
      <circle cx={32} cy={32} r={4.5} opacity={0.5} />
    </svg>
  )
}

/** Deep-groove ball bearing: two races, a cage of eight balls, a bore. */
export function BallBearing({ className, style }: PartProps) {
  const balls = Array.from({ length: 8 }, (_, i) => {
    const a = (i / 8) * Math.PI * 2 - Math.PI / 2
    return { cx: 32 + 15.5 * Math.cos(a), cy: 32 + 15.5 * Math.sin(a) }
  })
  return (
    <svg {...base} className={className} style={style} aria-hidden="true">
      <circle cx={32} cy={32} r={26} />
      <circle cx={32} cy={32} r={20} />
      <circle cx={32} cy={32} r={11} />
      <circle cx={32} cy={32} r={5.5} />
      {balls.map((b, i) => (
        <circle key={i} cx={Number(b.cx.toFixed(2))} cy={Number(b.cy.toFixed(2))} r={3.6} />
      ))}
    </svg>
  )
}

function spiral(cx: number, cy: number, r0: number, r1: number, turns: number) {
  const steps = Math.round(turns * 40)
  const pts: string[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const a = t * turns * Math.PI * 2
    const r = r0 + (r1 - r0) * t
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`)
  }
  return `M${pts.join('L')}`
}

/** Spiral wound gasket: outer centring ring, inner ring, and the wound filler between them —
 *  an actual Archimedean spiral, because concentric circles would be a different product. */
export function SpiralGasket({ className, style }: PartProps) {
  return (
    <svg {...base} className={className} style={style} aria-hidden="true">
      <circle cx={32} cy={32} r={27} />
      <circle cx={32} cy={32} r={23} />
      <circle cx={32} cy={32} r={10.5} />
      <circle cx={32} cy={32} r={7} />
      <path d={spiral(32, 32, 11.5, 22, 3.5)} strokeWidth={1.1} opacity={0.8} />
    </svg>
  )
}

/** Ball valve: flanged body, bored ball, stem and lever. */
export function BallValve({ className, style }: PartProps) {
  return (
    <svg {...base} className={className} style={style} aria-hidden="true">
      <path d="M4 26h11v14H4zM49 26h11v14H49z" />
      <path d="M15 27h6v12h-6zM43 27h6v12h-6z" opacity={0.45} />
      <circle cx={32} cy={33} r={16} />
      <circle cx={32} cy={33} r={9.5} />
      <path d="M22.5 33h19" />
      <path d="M32 17V9" />
      <path d="M24 9h16" />
    </svg>
  )
}
