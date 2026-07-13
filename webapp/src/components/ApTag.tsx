import type { ReactNode } from 'react'

// ApTag (DESIGN_SYSTEM §3 — контракт закрыт: status neutral/brand/success/attn).
// Padding 8×4, радиус chip, caption, без бордера. Синий/красный статусов НЕТ —
// «почти» состояние теперь neutral (§1: дисциплина акцента, не всё цветное).

export type TagStatus = 'neutral' | 'brand' | 'success' | 'attn'

// Бейджи — soft-подложка + ink-пара текста (дисциплина акцента §8: пилюли/бейджи
// НЕ несут сильный оранж; ink-пары держат AA на светлом).
const TONE: Record<TagStatus, string> = {
  neutral: 'bg-paper-2 text-label',
  brand: 'bg-brand-soft text-brand-ink',
  success: 'bg-success-soft text-success-ink',
  attn: 'bg-attn-soft text-attn-ink',
}

interface ApTagProps {
  status?: TagStatus
  children: ReactNode
  /** Ведущий мини-визуал (иконка/эмодзи) — цвет НЕ единственный сигнал. */
  leading?: ReactNode
  className?: string
}

export function ApTag({
  status = 'neutral',
  children,
  leading,
  className = '',
}: ApTagProps) {
  return (
    <span
      className={[
        'inline-flex shrink-0 items-center gap-1 rounded-chip px-2 py-1 text-caption1',
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
