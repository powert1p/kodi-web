import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { ApCard } from '../../components/ApCard'
import { RightIcon } from '../../icons'
import { StateChip } from './StateChip'

interface TaskCardProps {
  task: WrongTask
  /** Задержка stagger-reveal в мс. */
  delay: number
}

// Плитка-ошибка (ApCard as=button) — САМА тапается (hover → stroke-brand), без кнопки-дубля:
// «one primary action per screen» держит hero. Тема + таг-статус сверху, условие (KaTeX)
// в центре с клампом в 2 строки, снизу — что вышло в прошлый раз + тихий affordance «Разобрать ›».
export function TaskCard({ task, delay }: TaskCardProps) {
  const navigate = useNavigate()
  const style = { '--reveal-delay': `${delay}ms` } as CSSProperties

  return (
    <ApCard
      as="button"
      type="button"
      style={style}
      onClick={() => navigate(`/drill/${task.id}`)}
      aria-label={`Разобрать: ${task.topic_label}`}
      className="reveal flex w-full flex-col gap-3 text-left transition-colors hover:border-brand"
    >
      {/* Шапка: тема + таг состояния (тег прижат вправо) */}
      <div className="flex items-center gap-2">
        <span className="line-clamp-2 min-w-0 flex-1 text-title text-ink">
          {task.topic_label}
        </span>
        <StateChip state={task.state} />
      </div>

      {/* Условие — KaTeX, не больше двух строк (сканируемость списка) */}
      <p className="line-clamp-2 text-body text-text">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: что вышло в прошлый раз + тихий affordance перехода */}
      <div className="mt-0.5 flex items-center gap-3 border-t border-stroke pt-3">
        <span className="text-caption1 text-muted">
          в прошлый раз: <span className="font-num text-text">{task.wrong_answer}</span>
        </span>
        <span className="ml-auto inline-flex items-center gap-1 text-caption1-medium text-brand">
          Разобрать
          <RightIcon size={16} />
        </span>
      </div>
    </ApCard>
  )
}
