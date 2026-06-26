import { useNavigate } from 'react-router-dom'

interface DrillHeaderProps {
  topic: string
  /** Текущий шаг (1-based) и всего шагов лесенки. */
  current: number
  total: number
}

// Шапка разбора: кнопка «назад», тема, чанковая оранжевая полоса «шаг N из M».
// Намеренно тихая — boldness живёт в лесенке и фото-кнопке.
export function DrillHeader({ topic, current, total }: DrillHeaderProps) {
  const navigate = useNavigate()
  const ratio = total > 0 ? Math.min(current / total, 1) : 0
  const shown = Math.max(ratio, 0.06) * 100

  return (
    <header className="flex flex-col gap-2.5 pt-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label="Назад к срезу"
          className="flex size-11 shrink-0 items-center justify-center rounded-(--radius-button) border-[1.5px] border-border bg-surface text-ink transition-colors hover:bg-surface-soft hover:text-primary-ink active:scale-95"
        >
          <svg
            viewBox="0 0 24 24"
            className="size-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>

        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-[0.6rem] font-extrabold uppercase tracking-[0.16em] text-primary-ink">
            Работа над ошибкой
          </span>
          <span className="truncate font-display text-base font-extrabold leading-tight text-ink">
            {topic}
          </span>
        </div>

        <span className="font-num shrink-0 rounded-(--radius-pill) bg-surface-soft px-2.5 py-1 text-xs font-extrabold tabular-nums text-primary-ink">
          {current}/{total}
        </span>
      </div>

      {/* Чанковая полоса прогресса лесенки */}
      <div
        className="relative h-3.5 w-full overflow-hidden rounded-(--radius-pill) border border-border bg-surface-soft"
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={`Шаг ${current} из ${total}`}
      >
        <div
          className="relative h-full rounded-(--radius-pill) bg-primary transition-[width] duration-500 ease-out motion-reduce:transition-none"
          style={{ width: `${shown}%` }}
        >
          <span
            aria-hidden
            className="absolute inset-x-1 top-0.5 h-1 rounded-(--radius-pill) bg-white/35"
          />
        </div>
      </div>
    </header>
  )
}
