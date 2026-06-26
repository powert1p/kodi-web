import { useNavigate } from 'react-router-dom'
import { ApLinearProgress } from '../../components/ApLinearProgress'
import { LeftIcon } from '../../icons'

interface DrillHeaderProps {
  topic: string
  /** Текущий шаг (1-based) и всего шагов лесенки. */
  current: number
  total: number
}

// Шапка разбора в духе AiPlus App Bar (§8.5): back-кнопка (прозрачная,
// иконка text-primary), заголовок title + эйбров, тонкая полоса прогресса.
export function DrillHeader({ topic, current, total }: DrillHeaderProps) {
  const navigate = useNavigate()

  return (
    <header className="flex flex-col gap-3 pt-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label="Назад к срезу"
          className="flex size-11 shrink-0 items-center justify-center rounded-lg text-text-primary transition-colors hover:bg-bg-tertiary"
        >
          <LeftIcon size={22} />
        </button>

        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-caption2-medium uppercase tracking-[0.12em] text-text-brand">
            Работа над ошибкой
          </span>
          <span className="truncate text-title text-text-primary">{topic}</span>
        </div>

        {/* Счётчик/прогресс лесенки — только когда есть ступени (иначе «0/0» выглядит сломанным) */}
        {total > 0 && (
          <span className="font-num shrink-0 rounded-sm bg-bg-secondary px-2.5 py-1 text-caption2-medium tabular-nums text-text-dark-gray">
            {current}/{total}
          </span>
        )}
      </div>

      {total > 0 && (
        <ApLinearProgress
          value={current}
          max={total}
          minShown={0.04}
          ariaLabel={`Шаг ${current} из ${total}`}
        />
      )}
    </header>
  )
}
