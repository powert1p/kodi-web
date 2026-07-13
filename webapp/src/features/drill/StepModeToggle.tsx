interface StepModeToggleProps {
  mode: 'input' | 'tetrad'
  onChange: (m: 'input' | 'tetrad') => void
}

const SEGMENTS: { key: 'input' | 'tetrad'; label: string }[] = [
  { key: 'input', label: 'Ввод' },
  { key: 'tetrad', label: 'По тетради' },
]

// Сегмент-контрол «Ввод / По тетради»: переключает форму сдачи активной
// original-ступени. Активный сегмент — БЕЛЫЙ приподнятый чип (не оранж: сам
// переключатель не «действие», §8 дисциплина акцента — оранж бережём под CTA).
export function StepModeToggle({ mode, onChange }: StepModeToggleProps) {
  return (
    <div
      role="tablist"
      aria-label="Способ сдачи шага"
      className="inline-flex w-full gap-1 rounded-control border border-stroke bg-paper-3 p-1"
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
                ? 'lift-sm bg-surface text-ink'
                : 'bg-transparent text-muted hover:text-text',
            ].join(' ')}
          >
            {seg.label}
          </button>
        )
      })}
    </div>
  )
}
