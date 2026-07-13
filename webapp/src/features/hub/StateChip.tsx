import type { TaskState } from '../../lib/types'
import { ApTag } from '../../components/ApTag'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
  /** Переопределить подпись (напр. «Ты здесь» для ведущей карточки маршрута). */
  label?: string
  className?: string
}

// Поддерживающий мини-таг состояния (ApTag): ярлык-слово на мягкой тонированной
// подложке. Плоский — это не действие. Цвет НЕ единственный сигнал (слово-ярлык
// несёт смысл без цвета).
export function StateChip({ state, label, className }: StateChipProps) {
  const meta = STATE_META[state]
  return (
    <ApTag status={meta.tag} className={className}>
      {label ?? meta.label}
    </ApTag>
  )
}
