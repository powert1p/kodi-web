import type { ReactNode } from 'react'

// ApTag (AiPlus §8.3) — статусная плашка. Padding 8×4, радиус 8, caption1, без бордера.
// status → фон/текст по токенам. На цветных подложках текст контрастен (AA).

export type TagStatus = 'default' | 'error' | 'primary' | 'success' | 'info'

const TONE: Record<TagStatus, string> = {
  default: 'bg-bg-secondary text-text-dark-gray',
  error: 'bg-bg-error-secondary text-text-error',
  primary: 'bg-bg-light-brand-warning text-text-brand',
  success: 'bg-bg-success-light text-text-success',
  info: 'bg-bg-info text-text-info',
}

interface ApTagProps {
  status?: TagStatus
  children: ReactNode
  /** Ведущий мини-визуал (иконка/эмодзи) — цвет НЕ единственный сигнал. */
  leading?: ReactNode
  className?: string
}

export function ApTag({
  status = 'default',
  children,
  leading,
  className = '',
}: ApTagProps) {
  return (
    <span
      className={[
        'inline-flex shrink-0 items-center gap-1 rounded-sm px-2 py-1 text-caption1',
        TONE[status],
        className,
      ].join(' ')}
    >
      {leading && (
        <span aria-hidden className="flex items-center">
          {leading}
        </span>
      )}
      {children}
    </span>
  )
}
