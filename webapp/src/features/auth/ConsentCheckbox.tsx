import { CheckIcon } from '../../icons'

interface ConsentCheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

// Согласие на фото при регистрации — нативный <input type="checkbox"> (клавиатура/скринридер
// из коробки), поверх собственная стилизованная «коробка» токенами v11. Единственный кастомный
// контрол шага — сделан заметным (bounce на check), сама форма регистрации остаётся тихой.
// Регистрацию НЕ блокирует — согласие можно дать позже на хабе (см. ConsentCard).
export function ConsentCheckbox({ checked, onChange, disabled }: ConsentCheckboxProps) {
  return (
    <label className="flex items-start gap-3 rounded-control border border-stroke bg-surface p-3 transition-colors">
      <span className="relative h-11 w-11 shrink-0">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="peer absolute inset-0 h-11 w-11 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
        <span
          aria-hidden
          className={[
            'pointer-events-none absolute inset-0 m-auto flex h-6 w-6 items-center justify-center rounded-chip border transition-all peer-focus-visible:outline-3 peer-focus-visible:outline-offset-3 peer-focus-visible:outline-blue-deep',
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
        Я родитель или законный представитель. Разрешаю AiPlus обрабатывать фото решений
        для проверки заданий.
      </span>
    </label>
  )
}
