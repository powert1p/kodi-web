interface ApLinearProgressProps {
  /** Доля выполнения 0..1 (контракт DESIGN_SYSTEM §3). */
  value: number
  /** Подпись для скринридера. */
  ariaLabel: string
  /** Минимальная видимая доля заливки (0..1), чтобы полоса не «ломалась» на 0. */
  minShown?: number
  /** success — линия завершения темы/шага (§5 веха); по умолчанию brand. */
  tone?: 'brand' | 'success'
  className?: string
}

// ApLinearProgress (DESIGN_SYSTEM §3) — линейный прогресс. Высота 8, радиус full,
// трек paper-3, заливка route-line/success. Анимация ширины 300ms. Заливка — глубокий
// амбер route-line (3.3:1 к треку, R3 §1): часть языка маршрута, а не bright-CTA-оранж.
export function ApLinearProgress({
  value,
  ariaLabel,
  minShown = 0,
  tone = 'brand',
  className = '',
}: ApLinearProgressProps) {
  const ratio = Math.min(Math.max(value, 0), 1)
  const shown = Math.max(ratio, minShown) * 100

  return (
    <div
      className={['h-2 w-full overflow-hidden rounded-full bg-paper-3', className].join(' ')}
      role="progressbar"
      aria-valuenow={Math.round(ratio * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={ariaLabel}
    >
      <div
        className={[
          'h-full rounded-full transition-[width] duration-300 ease-out motion-reduce:transition-none',
          tone === 'success' ? 'bg-success' : 'bg-route-line',
        ].join(' ')}
        style={{ width: `${shown}%` }}
      />
    </div>
  )
}
