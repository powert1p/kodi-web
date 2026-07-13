import type { CSSProperties } from 'react'
import type { ErrorType } from '../../lib/types'
import { ApCard } from '../../components/ApCard'
import { ApTag } from '../../components/ApTag'

interface ErrorBarProps {
  item: ErrorType
  /** Доля от максимума (0..1) — длина полосы. */
  ratio: number
  /** Максимум повторений в списке (#1) — aria-valuemax метра (R3 §7). */
  max: number
  /** Ранг (1-based). #1 — «в фокусе», промотирован. */
  rank: number
  /** Задержка stagger-reveal, мс. */
  delay: number
}

// Чанковая горизонтальная полоса повторяемости ошибки (ranking = информация):
// трек stroke + заливка route-line (идиома прогресса, горизонтально). #1 — крупнее и
// помечен тагом «в фокусе». Ранг несёт отметка маршрута слева (RouteSpine), не строка.
// Один визуал на строку. Right-aligned число (моно).
export function ErrorBar({ item, ratio, max, rank, delay }: ErrorBarProps) {
  const isFocus = rank === 1
  const shown = Math.max(ratio, 0.08) * 100

  return (
    <ApCard
      as="article"
      padding="m"
      className={['reveal flex flex-col gap-2', isFocus ? 'lift-sm' : ''].join(' ')}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={[
              'min-w-0 truncate text-ink',
              isFocus ? 'text-title' : 'text-caption1-medium',
            ].join(' ')}
          >
            {item.label}
          </span>
          {isFocus && <ApTag status="brand">в фокусе</ApTag>}
        </div>
        <span className="font-display shrink-0 text-right text-h3 font-extrabold tabular-nums text-brand-ink">
          {item.count}
          <span className="ml-0.5 font-sans text-caption1 text-muted">×</span>
        </span>
      </div>

      {/* Полоса повторяемости */}
      <div
        className={[
          'relative w-full overflow-hidden rounded-full bg-stroke',
          isFocus ? 'h-2.5' : 'h-2',
        ].join(' ')}
        role="meter"
        aria-valuenow={item.count}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={`${item.label}: ${item.count} раз`}
      >
        <div
          className="h-full rounded-full bg-route-line transition-[width] duration-700 ease-out motion-reduce:transition-none"
          style={{ width: `${shown}%` }}
        />
      </div>

      {/* Последняя причина — только у #1, тихо; остальные строки чисты */}
      {isFocus && item.last_cause && (
        <p className="text-caption1 text-muted">Последний раз: {item.last_cause}</p>
      )}
    </ApCard>
  )
}
