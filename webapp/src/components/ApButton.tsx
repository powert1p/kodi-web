import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'inverse'
type Size = 'm' | 'l'

const SIZE: Record<Size, string> = {
  m: 'min-h-12 px-5',
  l: 'min-h-14 px-6',
}

const VARIANT: Record<Variant, string> = {
  primary:
    'border border-brand-deep/25 bg-brand text-on-brand shadow-key hover:bg-brand-deep hover:text-surface active:translate-y-1 active:shadow-none disabled:border-paper-3 disabled:bg-paper-3 disabled:text-label disabled:shadow-none',
  secondary:
    'border border-ink/30 bg-surface text-ink shadow-lift-sm hover:border-ink hover:bg-sage-soft disabled:border-stroke disabled:text-muted disabled:shadow-none',
  ghost:
    'border border-transparent bg-transparent text-text hover:border-stroke hover:bg-sage-soft disabled:text-muted',
  inverse:
    'border border-ink/25 bg-surface text-ink hover:border-brand hover:bg-brand-soft disabled:border-stroke disabled:text-muted',
}

interface ApButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  children: ReactNode
  variant?: Variant
  size?: Size
  full?: boolean
  loading?: boolean
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
        'inline-flex items-center justify-center gap-2 rounded-control text-title transition-[background-color,border-color,color,box-shadow,transform] duration-200',
        'disabled:cursor-not-allowed disabled:shadow-none',
        SIZE[size],
        VARIANT[variant],
        full ? 'w-full' : '',
        className,
      ].filter(Boolean).join(' ')}
      {...rest}
    >
      {loading ? <Spinner /> : children}
    </button>
  )
}

function Spinner() {
  return (
    <span className="inline-flex items-center gap-2" role="status">
      <svg width="20" height="20" viewBox="0 0 24 24" className="animate-spin motion-reduce:animate-none" aria-hidden>
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.24" />
        <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="square" />
      </svg>
      <span className="sr-only">Загрузка</span>
    </span>
  )
}
