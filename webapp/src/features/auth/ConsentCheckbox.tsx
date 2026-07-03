import { CheckIcon } from '../../icons'

interface ConsentCheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

// Согласие на фото при регистрации — нативный <input type="checkbox"> (клавиатура/скринридер
// из коробки), поверх собственная стилизованная «коробка» токенами v5. Единственный кастомный
// контрол шага — сделан заметным (bounce на check), сама форма регистрации остаётся тихой.
// Регистрацию НЕ блокирует — согласие можно дать позже на хабе (см. ConsentCard).
export function ConsentCheckbox({ checked, onChange, disabled }: ConsentCheckboxProps) {
  return (
    <label className="flex items-start gap-3 rounded-control border border-stroke bg-surface p-3 transition-colors">
      <span className="relative mt-0.5 h-6 w-6 shrink-0">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="absolute inset-0 h-6 w-6 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
        <span
          aria-hidden
          className={[
            'pointer-events-none flex h-6 w-6 items-center justify-center rounded-chip border transition-all',
            checked ? 'scale-105 border-brand bg-brand' : 'border-stroke bg-surface',
          ].join(' ')}
        >
          <CheckIcon
            size={13}
            className={['text-on-brand transition-opacity', checked ? 'opacity-100' : 'opacity-0'].join(' ')}
          />
        </span>
      </span>
      <span className="text-caption1 text-text">
        Разрешаю использовать фото работ моего ребёнка для обучения модели.{' '}
        <span className="text-muted">(текст на проверку юристу)</span>
      </span>
    </label>
  )
}
