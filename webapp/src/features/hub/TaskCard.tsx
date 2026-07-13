import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { ApCard } from '../../components/ApCard'
import { RightIcon } from '../../icons'
import { StateChip } from './StateChip'

interface TaskCardProps {
  task: WrongTask
  /** Ведущая карточка маршрута (текущая) — крафт-lift + «Ты здесь». */
  lead?: boolean
}

// Плитка-ошибка = остановка маршрута (ApCard as=button) — САМА тапается, без кнопки-дубля.
// Ведущая (current) карточка получает крафт-lift и метку «Ты здесь». Тема — display
// (Unbounded), условие (KaTeX) клампом в 2 строки, снизу — прошлый ответ + тихий переход.
export function TaskCard({ task, lead = false }: TaskCardProps) {
  const navigate = useNavigate()

  return (
    <ApCard
      as="button"
      type="button"
      onClick={() => navigate(`/drill/${task.id}`)}
      aria-label={`Разобрать: ${task.topic_label}`}
      className={[
        'flex w-full flex-col gap-3 text-left transition-shadow hover:border-brand',
        lead ? 'lift border-brand/40' : '',
      ].join(' ')}
    >
      {/* Шапка: тема (display) + метка «Ты здесь»/статус */}
      <div className="flex items-start gap-2">
        <span className="font-display line-clamp-2 min-w-0 flex-1 pt-0.5 text-title font-extrabold text-ink">
          {task.topic_label}
        </span>
        {lead ? <StateChip state="revisit" label="Ты здесь" /> : <StateChip state={task.state} />}
      </div>

      {/* Условие — учебный текст ≥18px (§5/R3 §6), KaTeX, не больше двух строк */}
      <p className="line-clamp-2 text-study text-text">
        <MathText text={task.statement} />
      </p>

      {/* Подвал: что вышло в прошлый раз + тихий affordance перехода */}
      <div className="mt-0.5 flex items-center gap-3 border-t border-stroke pt-3">
        <span className="text-caption1 text-muted">
          в прошлый раз: <span className="font-num text-text">{task.wrong_answer}</span>
        </span>
        <span className="ml-auto inline-flex items-center gap-1 text-caption1-medium text-brand-ink">
          Разобрать
          <RightIcon size={16} />
        </span>
      </div>
    </ApCard>
  )
}
