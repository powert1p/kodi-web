import { ApLinearProgress } from '../../components/ApLinearProgress'

interface ProgressBarProps {
  /** Сколько закрыто. */
  done: number
  /** Всего в срезе. */
  total: number
}

// Прогресс среза (AiPlus ApLinearProgress): тонкая полоса h8/r4, трек
// stroke-secondary + заливка stroke-brand. Подпись «%» справа, caption1.
export function ProgressBar({ done, total }: ProgressBarProps) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className="flex flex-col gap-2">
      <ApLinearProgress
        value={done}
        max={total}
        minShown={0.02}
        ariaLabel={`Закрыто ${done} из ${total}`}
      />
      <div className="flex items-center justify-between">
        <span className="text-caption1 text-text-secondary">Разобрано сегодня</span>
        <span className="font-num text-caption1-medium tabular-nums text-text-primary">
          {done}/{total} · {pct}%
        </span>
      </div>
    </div>
  )
}
