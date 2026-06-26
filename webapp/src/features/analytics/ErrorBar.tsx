import type { CSSProperties } from 'react'
import type { ErrorType } from '../../lib/types'

interface ErrorBarProps {
  item: ErrorType
  /** Доля от максимума (0..1) — длина полосы. */
  ratio: number
  /** Ранг (1-based). #1 — «в фокусе», промотирован. */
  rank: number
  /** Задержка stagger-reveal, мс. */
  delay: number
}

// Чанковая горизонтальная полоса повторяемости ошибки (идиома ProgressBar,
// повёрнутая горизонтально): утопленный тёплый трек + оранжевая заливка
// с внутренним бликом. #1 — выше и помечен пилюлей «в фокусе» (ранг = информация).
// Один визуал на строку (полоса) — без дельт/спарклайнов. Right-aligned число.
export function ErrorBar({ item, ratio, rank, delay }: ErrorBarProps) {
  const isFocus = rank === 1
  const shown = Math.max(ratio, 0.08) * 100

  return (
    <article
      className="card-flat reveal flex flex-col gap-2 rounded-(--radius-card) p-3.5"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="font-num shrink-0 text-[0.7rem] font-extrabold tabular-nums text-ink-mute">
            {rank}
          </span>
          <span
            className={[
              'min-w-0 truncate font-extrabold text-ink',
              isFocus ? 'text-[0.98rem]' : 'text-[0.9rem]',
            ].join(' ')}
          >
            {item.label}
          </span>
          {isFocus && (
            <span className="shrink-0 rounded-(--radius-pill) bg-primary px-2 py-0.5 text-[0.58rem] font-extrabold uppercase tracking-[0.1em] text-on-primary">
              в фокусе
            </span>
          )}
        </div>
        <span className="font-num shrink-0 text-right text-[0.95rem] font-extrabold tabular-nums text-primary-ink">
          {item.count}
          <span className="ml-0.5 text-[0.62rem] font-bold text-ink-mute">×</span>
        </span>
      </div>

      {/* Полоса повторяемости */}
      <div
        className={[
          'relative w-full overflow-hidden rounded-(--radius-pill) border border-border bg-surface-soft',
          isFocus ? 'h-4' : 'h-3',
        ].join(' ')}
        role="meter"
        aria-valuenow={item.count}
        aria-valuemin={0}
        aria-label={`${item.label}: ${item.count} раз`}
      >
        <div
          className="relative h-full rounded-(--radius-pill) bg-primary transition-[width] duration-700 ease-out motion-reduce:transition-none"
          style={{ width: `${shown}%` }}
        >
          <span
            aria-hidden
            className="absolute inset-x-1.5 top-0.5 h-1 rounded-(--radius-pill) bg-white/30"
          />
        </div>
      </div>

      {/* Последняя причина — только у #1, тихо; остальные строки чисты */}
      {isFocus && item.last_cause && (
        <p className="pl-5 text-xs font-bold leading-snug text-ink-mute">
          Последний раз: {item.last_cause}
        </p>
      )}
    </article>
  )
}
