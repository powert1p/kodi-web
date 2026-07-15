import { useState } from 'react'
import { MathText } from '../../components/MathText'
import { CheckIcon, DownIcon } from '../../icons'
import type { Rung } from '../../lib/ladder'
import { skillLabel } from './microSkillLabel'

interface RungQuietProps { rung: Rung; index: number }

export function RungSolved({ rung, index }: RungQuietProps) {
  const [open, setOpen] = useState(false)
  return (
    <article className="equation-commit rounded-control border border-success/20 border-l-4 border-l-success bg-success-soft px-4 py-5">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="grid min-h-11 w-full grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 text-left"
      >
        <span aria-hidden className="mt-1 flex size-6 items-center justify-center rounded-full bg-success text-surface"><CheckIcon size={12} /></span>
        <span className="min-w-0">
          <span className="block text-caption1-medium text-success-ink">{rung.kind === 'easier' ? 'Разминка' : `Шаг ${index}`} встроен в решение</span>
          <span className="font-display mt-2 inline-block text-3xl font-semibold text-ink">
            <span className="bracket-slot" data-state="done">{rung.submitted_value ?? 'Проверено'}</span>
          </span>
        </span>
        <span className={['mt-2 text-success-ink transition-transform', open ? 'rotate-180' : ''].join(' ')}><DownIcon size={15} /></span>
      </button>
      {open && (
        <div className="formula-body ml-9 mt-3 border-t border-success/25 pt-3 text-body text-text">
          <MathText text={rung.reveal ?? rung.instruction} />
        </div>
      )}
    </article>
  )
}

export function RungLocked({ rung, index }: RungQuietProps) {
  return (
    <div className="grid min-h-16 grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-control border border-dashed border-ink/15 bg-surface/45 px-3 py-4 text-muted">
      <span aria-hidden className="font-num text-caption1-medium">{String(index).padStart(2, '0')}</span>
      <span className="text-caption1-medium">{skillLabel(rung.microSkill) ?? 'Следующий шаг'}</span>
      <span className="text-caption2">впереди</span>
    </div>
  )
}
