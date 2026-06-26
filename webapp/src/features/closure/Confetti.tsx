import type { CSSProperties } from 'react'

// Лёгкое празднование закрытия: ~10 чипсов разлетаются из центра (transform/opacity).
// Детерминированный набор (без random при рендере) — стабильно в тестах/снапшотах.
// За пределами потока (absolute), decorative → aria-hidden. Reduced-motion гасит.
const CHIPS = [
  { x: -82, y: -52, r: 220, color: 'var(--bg-brand)', delay: 0 },
  { x: -38, y: -78, r: -180, color: 'var(--text-yellow)', delay: 40 },
  { x: 8, y: -88, r: 200, color: 'var(--bg-success)', delay: 20 },
  { x: 52, y: -74, r: -150, color: 'var(--text-info)', delay: 60 },
  { x: 88, y: -48, r: 240, color: 'var(--bg-brand)', delay: 30 },
  { x: -100, y: -10, r: 160, color: 'var(--text-yellow)', delay: 80 },
  { x: 100, y: -6, r: -200, color: 'var(--bg-success)', delay: 70 },
  { x: -62, y: 30, r: 180, color: 'var(--bg-brand)', delay: 100 },
  { x: 64, y: 34, r: -160, color: 'var(--text-yellow)', delay: 90 },
  { x: 0, y: 46, r: 220, color: 'var(--text-info)', delay: 120 },
] as const

export function Confetti() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-6 flex justify-center"
    >
      <div className="relative h-0 w-0">
        {CHIPS.map((c, i) => (
          <span
            key={i}
            className="confetti-chip absolute block size-2.5 rounded-[2px]"
            style={
              {
                backgroundColor: c.color,
                '--confetti-x': `${c.x}px`,
                '--confetti-y': `${c.y}px`,
                '--confetti-r': `${c.r}deg`,
                '--confetti-delay': `${c.delay}ms`,
              } as CSSProperties
            }
          />
        ))}
      </div>
    </div>
  )
}
