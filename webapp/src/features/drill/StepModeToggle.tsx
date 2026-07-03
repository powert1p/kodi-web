interface StepModeToggleProps {
  mode: 'input' | 'tetrad'
  onChange: (m: 'input' | 'tetrad') => void
}

const SEGMENTS: { key: 'input' | 'tetrad'; label: string }[] = [
  { key: 'input', label: 'Ввод' },
  { key: 'tetrad', label: 'По тетради' },
]

// Сегмент-контрол «Ввод / По тетради»: переключает форму сдачи активной
// original-ступени между текстовым полем и фото страницы тетради (DrillPage
// решает photoMode). Бренд-заливка — только активный сегмент (дисциплина
// акцента §1): переключатель сам по себе не «действие», действие — внутри.
export function StepModeToggle({ mode, onChange }: StepModeToggleProps) {
  return (
    <div
      role="tablist"
      aria-label="Способ сдачи шага"
      className="inline-flex w-full gap-1 rounded-control border border-stroke bg-surface p-1"
    >
      {SEGMENTS.map((seg) => {
        const active = mode === seg.key
        return (
          <button
            key={seg.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(seg.key)}
            className={[
              'h-12 flex-1 rounded-chip text-caption1-medium transition-colors',
              active
                ? 'bg-brand text-on-brand'
                : 'text-muted hover:bg-paper hover:text-text',
            ].join(' ')}
          >
            {seg.label}
          </button>
        )
      })}
    </div>
  )
}
