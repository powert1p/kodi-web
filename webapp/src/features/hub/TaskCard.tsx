import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { StateChip } from './StateChip'
import { STATE_META } from './stateConfig'

interface TaskCardProps {
  task: WrongTask
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Глиняная плитка-ошибка (тихая, дисциплинированная — boldness потрачена на hero-кольцо).
// Тема сверху (читаемо, не обрезается), математика в центре (KaTeX, скролл на обёртке),
// снизу — поддерживающий мини-маскот + CTA. Крупный тап-таргет, пружинный squish.
export function TaskCard({ task, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const meta = STATE_META[task.state]

  const style = {
    '--c': meta.accentVar,
    '--reveal-delay': `${delay}ms`,
  } as CSSProperties

  return (
    <button
      type="button"
      onClick={() => navigate(`/drill/${task.id}`)}
      style={style}
      className="clay press reveal group flex w-full flex-col gap-3 rounded-(--radius-tile) p-4 text-left"
    >
      {/* Шапка: тема + чип состояния */}
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden
            className="size-2.5 shrink-0 rounded-full bg-(--c)"
          />
          <span className="truncate text-sm font-extrabold text-ink-soft">
            {task.topic_label}
          </span>
        </span>
        <StateChip state={task.state} />
      </div>

      {/* Математика — крупная, со скроллом на обёртке */}
      <p className="text-[1.05rem] font-bold leading-snug text-ink">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: поддерживающая микрокопия + CTA */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <span className="text-xs font-bold text-ink-mute">{meta.hint}</span>
        <span className="inline-flex items-center gap-1 rounded-(--radius-pill) bg-brand px-3 py-1.5 text-xs font-extrabold text-on-brand transition-transform duration-200 ease-(--ease-spring) group-hover:translate-x-0.5 motion-reduce:transition-none">
          Разобрать
          <svg
            viewBox="0 0 16 16"
            className="size-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M3 8h9M9 4l4 4-4 4" />
          </svg>
        </span>
      </div>
    </button>
  )
}
