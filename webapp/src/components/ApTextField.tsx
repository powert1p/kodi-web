import type { InputHTMLAttributes, ReactNode } from 'react'

// ApTextField (AiPlus §8.2) — поле ввода. Радиус 12, текст body, filled-фон
// --bg-tertiary, бордер по состояниям: default --stroke-primary-disabled (1px),
// focus --stroke-brand (1.5px), error --stroke-error (1px). Лейбл --text-secondary.

interface ApTextFieldProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'size'> {
  /** Текст лейбла над полем (опц.). */
  label?: string
  /** Сообщение ошибки под полем (мягкий тон, НЕ карающий красный по умолчанию). */
  error?: string | null
  /** Иконка/виджет справа (suffix). */
  suffix?: ReactNode
  className?: string
  /** Высота поля: m=48 (default) / lg=56. */
  fieldSize?: 'm' | 'lg'
}

export function ApTextField({
  label,
  error,
  suffix,
  className = '',
  fieldSize = 'm',
  id,
  ...rest
}: ApTextFieldProps) {
  const isError = !!error
  return (
    <label className={['flex flex-col gap-1.5', className].join(' ')}>
      {label && (
        <span className="text-caption1-medium text-text-secondary">{label}</span>
      )}
      <div className="relative">
        <input
          id={id}
          className={[
            'w-full rounded-lg bg-bg-tertiary text-body text-text-primary',
            'placeholder:text-text-secondary',
            'px-4 outline-none transition-colors',
            fieldSize === 'lg' ? 'h-14' : 'h-12',
            suffix ? 'pr-11' : '',
            // бордер: 1px default → 1.5px brand на фокусе; error фиксированный
            isError
              ? 'border border-text-error'
              : 'border border-stroke-primary-disabled focus:border-[1.5px] focus:border-stroke-brand',
          ].join(' ')}
          style={{ fontSize: '16px' }}
          aria-invalid={isError}
          {...rest}
        />
        {suffix && (
          <span className="absolute inset-y-0 right-3 flex items-center text-text-secondary">
            {suffix}
          </span>
        )}
      </div>
      {error && (
        <span className="text-caption1 text-text-error">{error}</span>
      )}
    </label>
  )
}
