import { useId, type InputHTMLAttributes, type ReactNode } from 'react'

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
  const generatedId = useId()
  const fieldId = id ?? `ap-field-${generatedId}`
  const errorId = `${fieldId}-error`
  const describedBy = rest['aria-describedby']
  const inputProps = { ...rest }
  delete inputProps['aria-describedby']

  return (
    <div className={['flex flex-col gap-2', className].join(' ')}>
      {label && <label htmlFor={fieldId} className="text-caption1-medium text-muted">{label}</label>}
      <div className="relative">
        <input
          {...inputProps}
          id={fieldId}
          className={[
            'field-inset w-full rounded-control bg-surface text-body text-text',
            'placeholder:text-muted',
            'px-4 transition-colors',
            fieldSize === 'l' ? 'h-14' : 'h-12',
            suffix ? 'pr-11' : '',
            // бордер: 1px default → 1.5px brand на фокусе; error — амбер, не красный
            isError
              ? 'border border-oxide bg-oxide-soft/30'
              : 'border border-ink/20 focus:border-blue-deep',
          ].join(' ')}
          style={{ fontSize: '16px' }}
          aria-invalid={isError}
          aria-describedby={[describedBy, isError ? errorId : null].filter(Boolean).join(' ') || undefined}
        />
        {suffix && (
          <span className="absolute inset-y-0 right-3 flex items-center text-muted">
            {suffix}
          </span>
        )}
      </div>
      {error && <span id={errorId} className="text-caption1 text-oxide" role="alert" aria-live="polite">{error}</span>}
    </div>
  )
}
