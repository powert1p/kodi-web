import type { ButtonHTMLAttributes, ReactNode } from 'react'

// ApButton (DESIGN_SYSTEM §3 — контракт закрыт: variant/size/full/disabled/loading).
// primary — бренд-заливка, on-brand текст, radius-control. secondary — outlined
// бренд-бордер, brand текст. ghost — без фона/бордера, для тихих/back-действий.
// Размеры ТОЛЬКО m(48)/l(56) — тач-таргет ≥48 всегда (canon §1).

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'm' | 'l'

const SIZE: Record<Size, string> = {
  m: 'h-12 px-5', // 48
  l: 'h-14 px-6', // 56
}

const VARIANT: Record<Variant, string> = {
  primary: 'bg-brand text-on-brand hover:bg-brand-deep',
  secondary:
    'bg-transparent text-brand border border-brand hover:bg-brand-soft',
  ghost: 'bg-transparent text-text hover:bg-surface',
}

interface ApButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  children: ReactNode
  variant?: Variant
  size?: Size
  /** Растянуть на всю ширину. */
  full?: boolean
  /** Загрузка — блокирует клик, показывает спиннер. */
  loading?: boolean
  /** Доп. классы контейнера (layout, не цвет). */
  className?: string
}

export function ApButton({
  children,
  variant = 'primary',
  size = 'm',
  full = false,
  loading = false,
  className = '',
  type = 'button',
  disabled,
  ...rest
}: ApButtonProps) {
  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-control text-title transition-colors',
        'disabled:cursor-not-allowed disabled:bg-stroke disabled:text-muted disabled:border-transparent',
        SIZE[size],
        VARIANT[variant],
        full ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {loading ? <Spinner /> : children}
    </button>
  )
}

// Спиннер кнопки (наследует currentColor от варианта).
function Spinner() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" className="animate-spin" aria-hidden>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4" strokeDashoffset="10" opacity="0.35" />
      <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  )
}
