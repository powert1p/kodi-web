import type { InputHTMLAttributes, ReactNode } from 'react'

// ApTextField (DESIGN_SYSTEM §3 — контракт закрыт: size m/l · state default/error/disabled).
// Радиус control, текст body, фон surface, бордер по состояниям: default stroke (1px),
// focus brand (1.5px), error attn (НИКОГДА красный — §0/§2 запрет). Поле шага — l=56 (canon §1).

interface ApTextFieldProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'size'> {
  /** Текст лейбла над полем (опц.). */
  label?: string
  /** Сообщение под полем — мягкий тон (амбер, НЕ красный). */
  error?: string | null
  /** Иконка/виджет справа (suffix). */
  suffix?: ReactNode
  className?: string
  /** Высота поля: m=48 (default) / l=56 (учебный ввод — canon §1). */
  fieldSize?: 'm' | 'l'
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
    <label className={['flex flex-col gap-2', className].join(' ')}>
      {label && <span className="text-caption1-medium text-muted">{label}</span>}
      <div className="relative">
        <input
          id={id}
          className={[
            'w-full rounded-control bg-surface text-body text-text',
            'placeholder:text-muted',
            'px-4 outline-none transition-colors',
            fieldSize === 'l' ? 'h-14' : 'h-12',
            suffix ? 'pr-11' : '',
            // бордер: 1px default → 1.5px brand на фокусе; error — амбер, не красный
            isError
              ? 'border border-attn'
              : 'border border-stroke focus:border-[1.5px] focus:border-brand',
          ].join(' ')}
          style={{ fontSize: '16px' }}
          aria-invalid={isError}
          {...rest}
        />
        {suffix && (
          <span className="absolute inset-y-0 right-3 flex items-center text-muted">
            {suffix}
          </span>
        )}
      </div>
      {error && <span className="text-caption1 text-attn">{error}</span>}
    </label>
  )
}
