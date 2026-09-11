import type { ElementType } from 'react'

// A band of light passing along the text, in CSS rather than a motion library: one keyframe,
// a gradient clipped to the glyphs, no dependency. The band's width scales with the text so a
// short word and a long phrase shimmer at the same apparent speed.
export function TextShimmer({
  children,
  as: Tag = 'span',
  className = '',
  duration = 2,
  spread = 2,
}: {
  children: string
  as?: ElementType
  className?: string
  duration?: number
  spread?: number
}) {
  return (
    <Tag
      className={`text-shimmer ${className}`}
      style={{
        '--shimmer-spread': `${children.length * spread}px`,
        '--shimmer-duration': `${duration}s`,
      } as React.CSSProperties}
    >
      {children}
    </Tag>
  )
}
