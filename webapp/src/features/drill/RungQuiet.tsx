import { MathText } from '../../components/MathText'
import type { Rung } from '../../lib/ladder'

interface RungQuietProps {
  rung: Rung
  /** Метка ступени (1-based по оригиналам); easier помечается «разминка». */
  index: number
}

// Решённая ступень — слим-строка с зелёной галочкой (сворачивается, освобождает экран).
export function RungSolved({ rung, index }: RungQuietProps) {
  return (
    <div className="flex items-center gap-2.5 rounded-(--radius-field) border-[1.5px] border-got/25 bg-surface px-3 py-2.5">
      <span
        aria-hidden
        className="flex size-6 shrink-0 items-center justify-center rounded-full bg-got text-on-success"
      >
        <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 12l5 5 11-12" />
        </svg>
      </span>
      <span className="min-w-0 flex-1 truncate text-sm font-extrabold text-got-ink">
        <MathText text={rung.instruction} />
      </span>
      <span className="font-num shrink-0 text-[0.65rem] font-extrabold tabular-nums text-ink-mute">
        {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
      </span>
    </div>
  )
}

// Запертая ступень — затемнённая, без интерактива (виден маршрут впереди).
export function RungLocked({ rung, index }: RungQuietProps) {
  return (
    <div className="flex items-center gap-2.5 rounded-(--radius-field) border-[1.5px] border-border bg-surface px-3 py-2.5 opacity-55">
      <span
        aria-hidden
        className="flex size-6 shrink-0 items-center justify-center rounded-full border-[1.5px] border-border text-ink-mute"
      >
        <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 10V8a6 6 0 1 1 12 0v2M5 10h14v9H5z" />
        </svg>
      </span>
      <span className="min-w-0 flex-1 truncate text-sm font-bold text-ink-mute">
        {rung.microSkill}
      </span>
      <span className="font-num shrink-0 text-[0.65rem] font-extrabold tabular-nums text-ink-mute">
        {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
      </span>
    </div>
  )
}
