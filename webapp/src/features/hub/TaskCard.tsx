import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { RightIcon } from '../../icons'
import { StateChip } from './StateChip'

interface TaskCardProps {
  task: WrongTask
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Плитка-ошибка (AiPlus ApCard) — САМА тапается (hover → stroke-focus), без кнопки-дубля:
// «one primary action per screen» держит hero. Тема + таг-статус сверху, условие (KaTeX)
// в центре с клампом в 2 строки, снизу — что вышло в прошлый раз + тихий affordance «Разобрать ›».
export function TaskCard({ task, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const style = { '--reveal-delay': `${delay}ms` } as CSSProperties

  return (
    <button
      type="button"
      style={style}
      onClick={() => navigate(`/drill/${task.id}`)}
      aria-label={`Разобрать: ${task.topic_label}`}
      className="ap-card reveal flex w-full flex-col gap-3 p-4 text-left transition-colors hover:border-stroke-focus"
    >
      {/* Шапка: тема + таг состояния (тег прижат вправо) */}
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-title text-text-primary">
          {task.topic_label}
        </span>
        <StateChip state={task.state} />
      </div>

      {/* Условие — KaTeX, не больше двух строк (сканируемость списка) */}
      <p className="line-clamp-2 text-body text-text-primary">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: что вышло в прошлый раз + тихий affordance перехода */}
      <div className="mt-0.5 flex items-center gap-3 border-t border-stroke-secondary pt-3">
        <span className="text-caption1 text-text-secondary">
          в прошлый раз:{' '}
          <span className="font-num text-text-primary">{task.wrong_answer}</span>
        </span>
        <span className="ml-auto inline-flex items-center gap-1 text-caption1-medium text-text-brand">
          Разобрать
          <RightIcon size={16} />
        </span>
      </div>
    </button>
  )
}
