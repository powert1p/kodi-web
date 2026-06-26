import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'
import { RightIcon } from '../../icons'
import { StateChip } from './StateChip'
import { STATE_META } from './stateConfig'

interface TaskCardProps {
  task: WrongTask
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Плитка-ошибка (AiPlus ap-card, плоская, 1px-бордер). Тема + таг состояния сверху,
// математика (KaTeX) в центре, снизу — поддерживающая микрокопия + ApButton «Разобрать».
export function TaskCard({ task, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const meta = STATE_META[task.state]

  const style = {
    '--dot': meta.dotVar,
    '--reveal-delay': `${delay}ms`,
  } as CSSProperties

  return (
    <article style={style} className="ap-card reveal flex flex-col gap-3 p-4">
      {/* Шапка: тема + таг состояния */}
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <span aria-hidden className="size-2 shrink-0 rounded-full bg-(--dot)" />
          <span className="truncate text-caption1-medium text-text-primary">
            {task.topic_label}
          </span>
        </span>
        <StateChip state={task.state} />
      </div>

      {/* Математика — крупная, со скроллом на обёртке */}
      <p className="text-body text-text-primary">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: поддерживающая микрокопия + ApButton */}
      <div className="mt-0.5 flex items-center justify-between gap-3">
        <span className="text-caption2 text-text-secondary">{meta.hint}</span>
        <ApButton
          variant="filled"
          size="s"
          onClick={() => navigate(`/drill/${task.id}`)}
          aria-label={`Разобрать: ${task.topic_label}`}
        >
          Разобрать
          <RightIcon size={16} />
        </ApButton>
      </div>
    </article>
  )
}
