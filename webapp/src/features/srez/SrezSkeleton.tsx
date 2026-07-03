import type { CSSProperties } from 'react'
import { ApCard } from '../../components/ApCard'

// Loading: каркас той же формы (шапка + карточка + поле), чтобы содержимое не
// «прыгало» при появлении задач — тот же shimmer, что и у скелетонов хаба.
export function SrezSkeleton() {
  return (
    <div
      className="reveal flex flex-col gap-4"
      style={{ '--reveal-delay': '0ms' } as CSSProperties}
      aria-busy="true"
      aria-label="Готовим срез"
    >
      <header className="flex flex-col gap-3 pt-1">
        <div className="flex items-center justify-between gap-2">
          <div className="shimmer h-7 w-32 rounded-chip bg-surface" />
          <div className="shimmer h-6 w-16 rounded-chip bg-surface" />
        </div>
        <div className="shimmer h-2 w-full rounded-full bg-surface" />
      </header>

      <ApCard padding="m" className="flex flex-col gap-3">
        <div className="shimmer h-4 w-24 rounded-chip bg-paper" />
        <div className="shimmer h-6 w-full rounded-chip bg-paper" />
        <div className="shimmer h-14 w-full rounded-control bg-paper" />
      </ApCard>

      <p className="text-center text-caption1 text-muted">Готовим срез…</p>
    </div>
  )
}
