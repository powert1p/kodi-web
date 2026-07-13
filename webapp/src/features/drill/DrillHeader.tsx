import { useNavigate } from 'react-router-dom'
import { ApLinearProgress } from '../../components/ApLinearProgress'
import { LeftIcon } from '../../icons'

interface DrillHeaderProps {
  topic: string
  /** Текущий шаг (1-based) и всего шагов лесенки. */
  current: number
  total: number
}

// Шапка разбора + якорь первого вьюпорта (§3): топбар (back + крамб) → тема (display) →
// ДРОБЬ-АЛЬТИМЕТР «1/4» (Unbounded-гигант) с полосой подъёма. Дробь — сильная масса
// сверху; активная ступень ниже её продолжает якорь.
export function DrillHeader({ topic, current, total }: DrillHeaderProps) {
  const navigate = useNavigate()

  return (
    <header className="flex flex-col gap-4 pt-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label="Назад к срезу"
          className="flex size-12 shrink-0 items-center justify-center rounded-control border border-stroke bg-surface text-ink transition-colors hover:bg-paper-2"
        >
          <LeftIcon size={20} />
        </button>
        <span className="font-display text-caption1-medium uppercase tracking-[0.1em] text-label">
          Работа над ошибкой
        </span>
      </div>

      <h1 className="text-h1 text-ink">{topic}</h1>

      {total > 0 && (
        <div className="flex items-center gap-4">
          <span className="text-frac text-ink" aria-hidden>
            {current}
            <span className="den">/{total}</span>
          </span>
          <div className="flex flex-1 flex-col gap-2">
            <ApLinearProgress
              value={current / total}
              minShown={0.06}
              ariaLabel={`Ступень ${current} из ${total}`}
            />
            <span className="font-display text-caption1-medium text-ink">
              Ступень <span className="text-brand-ink">{current}</span> из {total} · подъём начат
            </span>
          </div>
        </div>
      )}
    </header>
  )
}
