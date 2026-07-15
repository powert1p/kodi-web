import { ApLinearProgress } from '../../components/ApLinearProgress'

interface ProgressBarProps {
  /** Сколько закрыто. */
  done: number
  /** Всего в срезе. */
  total: number
}

// Прогресс среза (ApLinearProgress): тонкая полоса h8/full, трек stroke +
// заливка brand. Подпись «%» справа, caption.
export function ProgressBar({ done, total }: ProgressBarProps) {
  const ratio = total > 0 ? done / total : 0
  const pct = Math.round(ratio * 100)

  return (
    <div className="flex flex-col gap-2">
      <ApLinearProgress
        value={ratio}
        minShown={0.02}
        ariaLabel={`Закрыто ${done} из ${total}`}
      />
      <div className="flex items-center justify-between">
        <span className="text-caption1 text-muted">Разобрано в списке</span>
        {/* «N из total» — та же система прочтения, что hero «N из total ждут разбора» (R4 §5) */}
        <span className="font-num text-caption1-medium tabular-nums text-text">
          {done} из {total} · {pct}%
        </span>
      </div>
    </div>
  )
}
