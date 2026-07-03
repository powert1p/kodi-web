import type { CSSProperties } from 'react'
import type { ErrorType } from '../../lib/types'
import { ApCard } from '../../components/ApCard'
import { ApTag } from '../../components/ApTag'

interface ErrorBarProps {
  item: ErrorType
  /** Доля от максимума (0..1) — длина полосы. */
  ratio: number
  /** Ранг (1-based). #1 — «в фокусе», промотирован. */
  rank: number
  /** Задержка stagger-reveal, мс. */
  delay: number
}

// Чанковая горизонтальная полоса повторяемости ошибки (ranking = информация):
// трек stroke + заливка brand (идиома прогресса, горизонтально). #1 — крупнее и
// помечен тагом «в фокусе». Один визуал на строку. Right-aligned число (моно).
export function ErrorBar({ item, ratio, rank, delay }: ErrorBarProps) {
  const isFocus = rank === 1
  const shown = Math.max(ratio, 0.08) * 100

  return (
    <ApCard
      as="article"
      padding="m"
      className="reveal flex flex-col gap-2"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="font-num shrink-0 text-caption2-medium tabular-nums text-muted">
            {rank}
          </span>
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
        <span className="font-num shrink-0 text-right text-title tabular-nums text-brand">
          {item.count}
          <span className="ml-0.5 text-caption2 text-muted">×</span>
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
        aria-label={`${item.label}: ${item.count} раз`}
      >
        <div
          className="h-full rounded-full bg-brand transition-[width] duration-700 ease-out motion-reduce:transition-none"
          style={{ width: `${shown}%` }}
        />
      </div>

      {/* Последняя причина — только у #1, тихо; остальные строки чисты */}
      {isFocus && item.last_cause && (
        <p className="pl-5 text-caption2 text-muted">Последний раз: {item.last_cause}</p>
      )}
    </ApCard>
  )
}
