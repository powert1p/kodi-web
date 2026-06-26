interface ProgressBarProps {
  /** Сколько закрыто. */
  done: number
  /** Всего в срезе. */
  total: number
}

// Большая скруглённая полоса прогресса урока (Duolingo-стиль).
// Утопленный трек (тёплая мягкая подложка) + оранжевая заливка со светлым
// внутренним бликом-капсулой сверху. Минимальная видимая ширина при 0 закрытых,
// чтобы полоса не казалась «сломанной».
export function ProgressBar({ done, total }: ProgressBarProps) {
  const ratio = total > 0 ? Math.min(done / total, 1) : 0
  const pct = Math.round(ratio * 100)
  const shown = Math.max(ratio, 0.04) * 100

  return (
    <div className="flex flex-col gap-1.5">
      <div
        className="relative h-5 w-full overflow-hidden rounded-(--radius-pill) border border-border bg-surface-soft"
        role="progressbar"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={`Закрыто ${done} из ${total}`}
      >
        <div
          className="relative h-full rounded-(--radius-pill) bg-primary transition-[width] duration-700 ease-out motion-reduce:transition-none"
          style={{ width: `${shown}%` }}
        >
          {/* Светлая капсула-блик внутри заливки — лёгкий объём без тяжёлых теней */}
          <span
            aria-hidden
            className="absolute inset-x-1.5 top-1 h-1.5 rounded-(--radius-pill) bg-white/30"
          />
        </div>
      </div>
      <div className="flex items-center justify-between px-0.5">
        <span className="text-xs font-bold text-ink-mute">
          Разобрано сегодня
        </span>
        <span className="font-num text-xs font-extrabold tabular-nums text-primary-ink">
          {done}/{total} · {pct}%
        </span>
      </div>
    </div>
  )
}
