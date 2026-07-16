// Сегмент-контрол выбора класса (4–7) при регистрации — тот же паттерн, что
// StepModeToggle в drill: бренд-заливка только у активного сегмента (дисциплина
// акцента v11), по умолчанию не выбрано ничего (value=null).

interface GradeSelectProps {
  value: number | null
  onChange: (grade: number) => void
  disabled?: boolean
  autoFocus?: boolean
}

// Классы, в которые может идти ученик (совпадает с валидацией backend: 4–7).
const GRADES = [4, 5, 6, 7] as const

export function GradeSelect({ value, onChange, disabled, autoFocus = false }: GradeSelectProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Класс"
      className="inline-flex w-full gap-1 rounded-control border border-stroke bg-paper p-1"
    >
      {GRADES.map((g) => {
        const active = value === g
        return (
          <button
            key={g}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            autoFocus={autoFocus && g === GRADES[0]}
            onClick={() => onChange(g)}
            className={[
              'font-display h-12 flex-1 rounded-chip text-title transition-colors',
              active
                ? 'bg-ink text-surface'
                : 'bg-transparent text-muted hover:bg-paper-2 hover:text-ink',
            ].join(' ')}
          >
            {g}
          </button>
        )
      })}
    </div>
  )
}
