import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { StateChip } from './StateChip'
import { STATE_META } from './stateConfig'

interface TaskCardProps {
  task: WrongTask
  /** Порядковый номер «репа» — крупная цифра в лейн-полосе. */
  index: number
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Signature: наклонная «энергетическая» лейн-полоса слева + крупный номер-реп.
// Цвет полосы кодирует состояние (поддерживающий светофор).
export function TaskCard({ task, index, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const meta = STATE_META[task.state]

  const style = {
    '--c': meta.accentVar,
    '--cd': meta.dimVar,
    '--reveal-delay': `${delay}ms`,
  } as CSSProperties

  return (
    <button
      type="button"
      onClick={() => navigate(`/drill/${task.id}`)}
      style={style}
      className="reveal group relative flex w-full items-stretch gap-3 overflow-hidden rounded-(--radius-card) border border-line/60 bg-surface text-left transition-transform duration-200 ease-(--ease-out-energy) active:scale-[0.985] hover:border-[color-mix(in_oklab,var(--c)_50%,var(--color-line))] motion-reduce:transition-none"
    >
      {/* Наклонная лейн-полоса с номером-репом (signature element) */}
      <div className="relative w-[4.25rem] shrink-0 self-stretch">
        <div
          aria-hidden
          className="absolute -inset-y-3 left-[-30%] w-[150%] -skew-x-6 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--c)_85%,transparent),color-mix(in_oklab,var(--cd)_90%,transparent))]"
        />
        <span className="font-num absolute inset-0 flex items-center justify-center text-3xl font-bold text-brand-ink/90 tabular-nums">
          {String(index).padStart(2, '0')}
        </span>
      </div>

      {/* Контент */}
      <div className="flex min-w-0 flex-1 flex-col gap-2.5 py-4 pr-4">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-xs font-semibold uppercase tracking-wider text-ink-mute">
            {task.topic_label}
          </span>
          <StateChip state={task.state} />
        </div>

        <p className="text-[0.95rem] leading-snug text-ink">
          <MathText text={task.statement} />
        </p>

        <div className="flex items-center justify-between gap-2 pt-0.5">
          <span className="text-xs text-ink-mute">{meta.hint}</span>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-(--c) transition-transform duration-200 group-hover:translate-x-0.5 motion-reduce:transition-none">
            Разобрать
            <svg
              viewBox="0 0 16 16"
              className="size-3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="M3 8h9M9 4l4 4-4 4" />
            </svg>
          </span>
        </div>
      </div>
    </button>
  )
}
