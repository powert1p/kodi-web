interface StepModeToggleProps {
  mode: 'input' | 'tetrad'
  onChange: (mode: 'input' | 'tetrad') => void
  disabled?: boolean
}

const SEGMENTS = [{ key: 'input', label: 'Ввод' }, { key: 'tetrad', label: 'По тетради' }] as const

export function StepModeToggle({ mode, onChange, disabled = false }: StepModeToggleProps) {
  return (
    <div role="tablist" aria-label="Способ сдачи шага" className="inline-flex rounded-chip border border-ink/15 bg-paper p-1">
      {SEGMENTS.map((segment) => {
        const active = mode === segment.key
        return (
          <button
            key={segment.key}
            type="button"
            role="tab"
            aria-selected={active}
            disabled={disabled}
            onClick={() => onChange(segment.key)}
            className={['min-h-11 rounded-chip px-3 text-caption1-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 sm:min-h-12 sm:px-4', active ? 'bg-ink text-surface' : 'text-muted hover:bg-sage-soft hover:text-ink'].join(' ')}
          >
            {segment.label}
          </button>
        )
      })}
    </div>
  )
}
