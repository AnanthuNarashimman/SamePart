// Eight pixels lighting in turn around a diamond. Sits in currentColor so it takes the text
// colour of wherever it is placed; size it with the className (h-4 w-4 by default).
export function Diamond({ className = 'h-4 w-4', ...props }: React.ComponentProps<'svg'>) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      role="status"
      aria-label="Loading"
      className={className}
      {...props}
    >
      {[
        [8, 0], [12, 4], [16, 8], [12, 12], [8, 16], [4, 12], [0, 8], [4, 4],
      ].map(([x, y], i) => (
        <rect
          key={i}
          x={x}
          y={y}
          width="4"
          height="4"
          className="diamond-pixel"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </svg>
  )
}
