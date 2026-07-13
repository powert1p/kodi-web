import { useState } from 'react'
import { MathText } from '../../components/MathText'
import { CheckIcon, DownIcon } from '../../icons'
import type { Rung } from '../../lib/ladder'
import { skillLabel } from './microSkillLabel'

interface RungQuietProps {
  rung: Rung
  /** Метка ступени (1-based по оригиналам); easier помечается «разминка». */
  index: number
}

// Решённая ступень — слим-строка с зелёной галочкой (success-тон). Текст шага
// клампится в 2 строки, но НЕ обрезается безвозвратно (canon §2 п.3) — тап
// разворачивает/сворачивает полный текст.
export function RungSolved({ rung, index }: RungQuietProps) {
  const [open, setOpen] = useState(false)

  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      aria-expanded={open}
      className="flex w-full items-start gap-3 rounded-control border border-success/30 bg-success-soft px-3 py-3 text-left"
    >
      <span
        aria-hidden
        className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-success text-on-brand"
      >
        <CheckIcon size={12} />
      </span>
      <span
        className={[
          'min-w-0 flex-1 text-caption1-medium text-success-ink',
          open ? '' : 'line-clamp-2',
        ].join(' ')}
      >
        <MathText text={rung.instruction} />
      </span>
      <span className="flex shrink-0 items-center gap-2">
        <span className="font-num text-caption2 tabular-nums text-muted">
          {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
        </span>
        <span className={['text-muted transition-transform', open ? 'rotate-180' : ''].join(' ')}>
          <DownIcon size={14} />
        </span>
      </span>
    </button>
  )
}

// Запертая ступень — «призрак» (§3): компактная, низкий контраст, штрих-бордер.
// Виден маршрут впереди, но без веса активной ступени.
export function RungLocked({ rung, index }: RungQuietProps) {
  return (
    <div className="flex items-center gap-3 rounded-control border border-dashed border-grid-strong bg-paper-2 px-3 py-3 opacity-70">
      <span
        aria-hidden
        className="flex size-6 shrink-0 items-center justify-center rounded-full border border-grid-strong text-muted"
      >
        <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 10V8a6 6 0 1 1 12 0v2M5 10h14v9H5z" />
        </svg>
      </span>
      <span className="line-clamp-1 min-w-0 flex-1 text-caption1 text-muted">
        {skillLabel(rung.microSkill) ?? 'Этот шаг'}
      </span>
      <span className="font-num shrink-0 text-caption2 tabular-nums text-muted">
        {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
      </span>
    </div>
  )
}
