interface ApLinearProgressProps {
  /** Текущее значение. */
  value: number
  /** Максимум. */
  max: number
  /** Подпись для скринридера. */
  ariaLabel: string
  /** Минимальная видимая доля заливки (0..1), чтобы полоса не «ломалась» на 0. */
  minShown?: number
  className?: string
}

// ApLinearProgress (AiPlus §8.3) — линейный прогресс. Высота 8, радиус 4,
// трек --stroke-secondary, заливка --stroke-brand. Анимация ширины 300ms.
export function ApLinearProgress({
  value,
  max,
  ariaLabel,
  minShown = 0,
  className = '',
}: ApLinearProgressProps) {
  const ratio = max > 0 ? Math.min(value / max, 1) : 0
  const shown = Math.max(ratio, minShown) * 100

  return (
    <div
      className={[
        'h-2 w-full overflow-hidden rounded-xs bg-stroke-secondary',
        className,
      ].join(' ')}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={ariaLabel}
    >
      <div
        className="h-full rounded-xs bg-stroke-brand transition-[width] duration-300 ease-out motion-reduce:transition-none"
        style={{ width: `${shown}%` }}
      />
    </div>
  )
}
