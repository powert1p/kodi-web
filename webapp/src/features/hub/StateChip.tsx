import type { TaskState } from '../../lib/types'
import { ApTag } from '../../components/ApTag'
import { STATE_META } from './stateConfig'

interface StateChipProps {
  state: TaskState
}

// Поддерживающий мини-таг состояния (AiPlus ApTag): эмодзи + ярлык на мягкой
// тонированной подложке. Плоский — это не действие. Цвет НЕ единственный сигнал.
export function StateChip({ state }: StateChipProps) {
  const meta = STATE_META[state]
  return (
    <ApTag
      status={meta.tag}
      leading={<span className="text-[0.8rem] leading-none">{meta.emoji}</span>}
    >
      {meta.label}
    </ApTag>
  )
}
