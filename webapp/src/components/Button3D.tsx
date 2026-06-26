import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'

// SIGNATURE-компонент: чанковая 3D push-кнопка в духе Duolingo.
// Сплошная заливка + сплошной тёмный нижний край (box-shadow без блюра).
// Механическое нажатие (translateY + схлоп края) живёт в .btn-3d (index.css).
// Boldness проекта потрачена здесь — всё остальное держим тихим и плоским.

type Variant = 'primary' | 'success' | 'secondary'
type Size = 'md' | 'lg'

// Заливка / край / цвет текста на вариант. secondary — тёплый «контурный» вид.
const VARIANT: Record<Variant, { fill: string; edge: string; ink: string }> = {
  primary: {
    fill: 'var(--color-primary)',
    edge: 'var(--color-primary-edge)',
    ink: 'var(--color-on-primary)',
  },
  success: {
    fill: 'var(--color-success)',
    edge: 'var(--color-success-edge)',
    ink: 'var(--color-on-success)',
  },
  secondary: {
    fill: 'var(--color-surface)',
    edge: 'var(--color-border)',
    ink: 'var(--color-ink)',
  },
}

const SIZE: Record<Size, string> = {
  md: 'h-12 px-5 text-sm',
  lg: 'h-14 px-6 text-base',
}

interface Button3DProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  children: ReactNode
  variant?: Variant
  size?: Size
  /** Растянуть на всю ширину родителя. */
  block?: boolean
  /** Доп. классы контейнера (layout, не цвет). */
  className?: string
}

export function Button3D({
  children,
  variant = 'primary',
  size = 'md',
  block = false,
  className = '',
  type = 'button',
  ...rest
}: Button3DProps) {
  const v = VARIANT[variant]
  const isSecondary = variant === 'secondary'

  const style = {
    '--edge': v.edge,
    backgroundColor: v.fill,
    color: v.ink,
    // secondary получает видимый бордер (плоская кнопка-«призрак» на креме)
    border: isSecondary ? '1.5px solid var(--color-border)' : undefined,
  } as CSSProperties

  return (
    <button
      type={type}
      style={style}
      className={[
        'btn-3d inline-flex items-center justify-center gap-2 rounded-(--radius-button)',
        'font-display font-extrabold tracking-tight',
        'disabled:cursor-not-allowed disabled:opacity-60',
        SIZE[size],
        block ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </button>
  )
}
