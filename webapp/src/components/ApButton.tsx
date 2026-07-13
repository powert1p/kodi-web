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

// primary — заливка brand + ink-текст (AA 7:1, НЕ белый) + display-шрифт и «ключ»-тень
// (единственная брендовая масса действия). secondary — outlined brand-ink (AA на светлом).
// ghost — тихие/back-действия. disabled — per-variant: primary остаётся «живой» в brand-soft
// с brand-ink текстом (честно-неактивна, не мёртво-серая — brand-ink на brand-soft = 4.95:1,
// R4 §5); secondary/ghost гасятся тихо в paper-3/label.
const VARIANT: Record<Variant, string> = {
  primary:
    'bg-brand text-on-brand hover:bg-brand-deep font-display font-extrabold shadow-key active:translate-y-px disabled:bg-brand-soft disabled:text-brand-ink',
  secondary:
    'bg-surface text-brand-ink border border-brand/40 hover:bg-brand-soft disabled:bg-paper-3 disabled:text-label',
  ghost: 'bg-transparent text-text hover:bg-paper-2 disabled:bg-transparent disabled:text-label',
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
        // disabled — общая механика (курсор/бордер/тень снимаются); цвет заливки и текста
        // задаёт КАЖДЫЙ вариант отдельно (VARIANT): primary «живая» в brand-soft, тихие — в
        // paper-3/label. Оба ≥4.5:1 (R4 §5; было единое text-muted 2.98:1 → R3 → R4).
        'disabled:cursor-not-allowed disabled:border-transparent disabled:shadow-none',
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
