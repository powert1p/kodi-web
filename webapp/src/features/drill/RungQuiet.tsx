import { MathText } from '../../components/MathText'
import { CheckIcon } from '../../icons'
import type { Rung } from '../../lib/ladder'

interface RungQuietProps {
  rung: Rung
  /** Метка ступени (1-based по оригиналам); easier помечается «разминка». */
  index: number
}

// Решённая ступень — слим-строка с зелёной галочкой (AiPlus success-тон).
export function RungSolved({ rung, index }: RungQuietProps) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-stroke-success-light bg-bg-success-light px-3 py-2.5">
      <span
        aria-hidden
        className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-success text-text-tertiary"
      >
        <CheckIcon size={12} />
      </span>
      <span className="min-w-0 flex-1 truncate text-caption1-medium text-text-success">
        <MathText text={rung.instruction} />
      </span>
      <span className="font-num shrink-0 text-caption2 tabular-nums text-text-secondary">
        {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
      </span>
    </div>
  )
}

// Запертая ступень — затемнённая, без интерактива (виден маршрут впереди).
export function RungLocked({ rung, index }: RungQuietProps) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-stroke-primary-disabled bg-bg-tertiary px-3 py-2.5 opacity-60">
      <span
        aria-hidden
        className="flex size-6 shrink-0 items-center justify-center rounded-full border border-stroke-primary-disabled text-text-secondary"
      >
        <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 10V8a6 6 0 1 1 12 0v2M5 10h14v9H5z" />
        </svg>
      </span>
      <span className="min-w-0 flex-1 truncate text-caption1 text-text-secondary">
        {rung.microSkill}
      </span>
      <span className="font-num shrink-0 text-caption2 tabular-nums text-text-secondary">
        {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
      </span>
    </div>
  )
}
