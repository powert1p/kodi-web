import type { ReactNode } from 'react'

// ApInformer (v11 — tone neutral/brand/attn/success). Brand — редкий action/context accent.
// (brand-soft подложка = «голос Кёди», мягкий тинт, НЕ сильный оранж действия §8).
// neutral — нейтральный факт (бумага). attn — «не сошлось» (амбер, НИКОГДА красный).
// success — закрытие/веха. Синий упразднён. Ink-пары акцента держат AA на светлом.
export type InformerTone = 'neutral' | 'brand' | 'attn' | 'success'

const TONE: Record<InformerTone, { box: string; accent: string }> = {
  neutral: { box: 'bg-paper-2 border-stroke', accent: 'text-text' },
  brand: { box: 'bg-brand-soft border-brand/45', accent: 'text-brand-ink' },
  attn: { box: 'bg-attn-soft border-attn/30', accent: 'text-attn-ink' },
  success: { box: 'bg-success-soft border-success/30', accent: 'text-success-ink' },
}

interface ApInformerProps {
  tone?: InformerTone
  /** Заголовок (title). */
  title?: ReactNode
  /** Тело (учебный текст — реплика Кёди, ≥18px на вызывающей стороне при необходимости). */
  children: ReactNode
  /** Ведущий визуал слева (иконка/маскот) — тонируется accent через text-current. */
  leading?: ReactNode
  /** role для скринридера (status по умолчанию — мягкое объявление). */
  role?: 'status' | 'alert'
  className?: string
}

export function ApInformer({
  tone = 'neutral',
  title,
  children,
  leading,
  role = 'status',
  className = '',
}: ApInformerProps) {
  const t = TONE[tone]
  return (
    <div
      role={role}
      className={[
        'flex w-full items-start gap-3 rounded-control border border-l-4 p-4',
        t.box,
        className,
      ].join(' ')}
    >
      {leading && (
        <span className={['mt-0.5 flex shrink-0 items-center', t.accent].join(' ')}>
          {leading}
        </span>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        {title && <span className={['text-title', t.accent].join(' ')}>{title}</span>}
        <div className="text-caption1 text-text">{children}</div>
      </div>
    </div>
  )
}
