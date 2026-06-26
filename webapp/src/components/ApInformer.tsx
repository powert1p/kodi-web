import type { ReactNode } from 'react'

// ApInformer / Banner (AiPlus §8.4) — баннер-информер. width 100%, padding 12,
// радиус 12, бордер 1px. Заголовок title/--text-primary, подзаголовок caption1.
// type → фон/бордер/акцент по токенам. info(default)/warning/success/error.

export type InformerType = 'info' | 'warning' | 'success' | 'error'

const TONE: Record<
  InformerType,
  { box: string; accent: string }
> = {
  info: { box: 'bg-bg-info border-stroke-info', accent: 'text-text-info' },
  warning: {
    box: 'bg-bg-light-brand-warning border-stroke-brand-light',
    accent: 'text-text-brand',
  },
  success: {
    box: 'bg-bg-success-light border-stroke-success-light',
    accent: 'text-text-success',
  },
  error: {
    box: 'bg-bg-error-tertiary border-stroke-error-light',
    accent: 'text-text-error',
  },
}

interface ApInformerProps {
  type?: InformerType
  /** Заголовок (title). */
  title?: ReactNode
  /** Тело (caption1). */
  children: ReactNode
  /** Ведущий визуал слева (иконка/маскот) — тонируется accent через text-current. */
  leading?: ReactNode
  /** role для скринридера (status по умолчанию — мягкое объявление). */
  role?: 'status' | 'alert'
  className?: string
}

export function ApInformer({
  type = 'info',
  title,
  children,
  leading,
  role = 'status',
  className = '',
}: ApInformerProps) {
  const tone = TONE[type]
  return (
    <div
      role={role}
      className={[
        'flex w-full items-start gap-2.5 rounded-lg border p-3',
        tone.box,
        className,
      ].join(' ')}
    >
      {leading && (
        <span className={['mt-0.5 flex shrink-0 items-center', tone.accent].join(' ')}>
          {leading}
        </span>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        {title && (
          <span className={['text-title', tone.accent].join(' ')}>{title}</span>
        )}
        <div className="text-caption1 text-text-primary">{children}</div>
      </div>
    </div>
  )
}
