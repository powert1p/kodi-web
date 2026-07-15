import type { LearningRole } from '../../lib/types'

const PHASES: Array<{ role: LearningRole; number: string; label: string; detail: string }> = [
  { role: 'worked', number: '01', label: 'Пример', detail: 'Смотрим метод' },
  { role: 'guided', number: '02', label: 'Вместе', detail: 'Снимаем опоры' },
  { role: 'independent', number: '03', label: 'Сам', detail: 'Решаешь без шагов' },
  { role: 'transfer', number: '04', label: 'Перенос', detail: 'Новая ситуация' },
]

interface LearningPhaseRailProps {
  role: LearningRole | null
  completed: boolean
}

export function LearningPhaseRail({ role, completed }: LearningPhaseRailProps) {
  const activeIndex = role ? PHASES.findIndex((phase) => phase.role === role) : -1
  return (
    <nav aria-label="Этапы урока" className="learning-phase-nav">
      <p className="hidden text-mark text-brand-deep lg:block">Маршрут урока</p>
      <ol className="learning-phase-rail">
        {PHASES.map((phase, index) => {
          const state = completed || index < activeIndex
            ? 'done'
            : index === activeIndex
              ? 'active'
              : 'todo'
          return (
            <li
              key={phase.role}
              className="learning-phase-item"
              data-state={state}
              aria-current={state === 'active' ? 'step' : undefined}
            >
              <span className="learning-phase-node" aria-hidden>
                {state === 'done' ? '✓' : phase.number}
              </span>
              <span
                className="learning-phase-label"
                aria-current={state === 'active' ? 'step' : undefined}
              >
                {phase.label}
              </span>
              <span className="learning-phase-detail">{phase.detail}</span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
