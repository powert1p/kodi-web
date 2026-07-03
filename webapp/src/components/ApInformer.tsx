import type { ReactNode } from 'react'

// ApInformer (DESIGN_SYSTEM §3 — контракт закрыт: tone neutral/attn/success).
// Синий tone упразднён — четвёртому акценту взяться неоткуда (§1). neutral —
// спокойная поддерживающая реплика Кёди/факт (бумажная подложка, без бренда —
// брендовый акцент живёт ТОЛЬКО в реальном CTA). attn — «не сошлось» (амбер,
// НИКОГДА красный). success — закрытие/веха.

export type InformerTone = 'neutral' | 'attn' | 'success'

const TONE: Record<InformerTone, { box: string; accent: string }> = {
  neutral: { box: 'bg-paper border-stroke', accent: 'text-text' },
  attn: { box: 'bg-attn-soft border-attn/30', accent: 'text-attn' },
  success: { box: 'bg-success-soft border-success/30', accent: 'text-success' },
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
        'flex w-full items-start gap-3 rounded-control border p-3',
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
