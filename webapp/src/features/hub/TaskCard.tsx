import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { Button3D } from '../../components/Button3D'
import { StateChip } from './StateChip'
import { STATE_META } from './stateConfig'

interface TaskCardProps {
  task: WrongTask
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Плоская плитка-ошибка (тихая, дисциплинированная — boldness живёт в 3D-кнопке).
// Тема сверху (читаемо, не обрезается), математика в центре (KaTeX, скролл на обёртке),
// снизу — поддерживающая микрокопия + чанковая 3D-кнопка «Разобрать».
export function TaskCard({ task, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const meta = STATE_META[task.state]

  const style = {
    '--c': meta.accentVar,
    '--reveal-delay': `${delay}ms`,
  } as CSSProperties

  return (
    <article
      style={style}
      className="card-flat reveal flex flex-col gap-3 rounded-(--radius-tile) p-4"
    >
      {/* Шапка: тема + чип состояния */}
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <span aria-hidden className="size-2.5 shrink-0 rounded-full bg-(--c)" />
          <span className="truncate text-sm font-extrabold text-ink">
            {task.topic_label}
          </span>
        </span>
        <StateChip state={task.state} />
      </div>

      {/* Математика — крупная, со скроллом на обёртке */}
      <p className="text-[1.05rem] font-bold leading-snug text-ink">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: поддерживающая микрокопия + чанковая 3D-кнопка */}
      <div className="mt-0.5 flex items-center justify-between gap-3">
        <span className="text-xs font-bold text-ink-mute">{meta.hint}</span>
        <Button3D
          variant="primary"
          size="md"
          onClick={() => navigate(`/drill/${task.id}`)}
          aria-label={`Разобрать: ${task.topic_label}`}
        >
          Разобрать
          <svg
            viewBox="0 0 16 16"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M3 8h9M9 4l4 4-4 4" />
          </svg>
        </Button3D>
      </div>
    </article>
  )
}
