import type { ButtonHTMLAttributes, ReactNode } from 'react'

// ApButton (AiPlus §8.1) — плоская кнопка. Бренд-заливка #FF8C00, текст белый
// (--text-tertiary), радиус 12, БЕЗ 3D-края/тени. hover/pressed → bg-brand-hovered.
// Размеры m=48 / s=40 / xs=32. Варианты: filled (default), outlined, error.
// gap иконка↔текст 8. Заменяет прежнюю чанковую Button3D.

type Variant = 'filled' | 'outlined'
type Size = 'm' | 's' | 'xs'

const SIZE: Record<Size, string> = {
  m: 'h-12 px-5', // 48
  s: 'h-10 px-4', // 40
  xs: 'h-8 px-4 text-caption1-medium', // 32, мельче текст
}

interface ApButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  children: ReactNode
  variant?: Variant
  size?: Size
  /** Растянуть на всю ширину (isExpanded). */
  block?: boolean
  /** Ошибочное действие — мягкая красная заливка/текст (НЕ карающая). */
  isError?: boolean
  /** Загрузка — блокирует клик, показывает спиннер. */
  isLoading?: boolean
  /** Доп. классы контейнера (layout, не цвет). */
  className?: string
}

export function ApButton({
  children,
  variant = 'filled',
  size = 'm',
  block = false,
  isError = false,
  isLoading = false,
  className = '',
  type = 'button',
  disabled,
  ...rest
}: ApButtonProps) {
  const isDisabled = disabled || isLoading

  // Цвета по варианту/состоянию (AiPlus §8.1).
  let tone: string
  if (isError) {
    tone =
      variant === 'outlined'
        ? 'bg-bg-error-tertiary text-text-error border border-text-error'
        : 'bg-bg-error-tertiary text-text-error'
  } else if (variant === 'outlined') {
    tone =
      'bg-transparent text-text-brand border border-bg-brand hover:bg-bg-light-brand-warning'
  } else {
    tone = 'bg-bg-brand text-text-tertiary hover:bg-bg-brand-hovered'
  }

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg text-title transition-colors',
        'disabled:cursor-not-allowed disabled:bg-bg-disabled disabled:text-text-disabled disabled:border-transparent',
        SIZE[size],
        tone,
        block ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {isLoading ? <Spinner /> : children}
    </button>
  )
}

// Спиннер кнопки (--text-tertiary на заливке, наследует currentColor).
function Spinner() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" className="animate-spin" aria-hidden>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4" strokeDashoffset="10" opacity="0.35" />
      <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  )
}
