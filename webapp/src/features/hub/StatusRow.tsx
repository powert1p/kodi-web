import { HistoryIcon, StarFilledIcon } from '../../icons'

interface StatusRowProps {
  /** Дни подряд (streak). */
  streak: number
  /** Накопленные очки/XP. */
  points: number
}

// Верхняя статус-строка: streak (часы) + XP (звезда). Плоские пилюли —
// surface на paper-подложке, 1px stroke, радиус full. Табличные цифры.
export function StatusRow({ streak, points }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="inline-flex items-center gap-2 rounded-full border border-stroke bg-surface px-3 py-2">
        <span className="text-brand">
          <HistoryIcon size={18} />
        </span>
        <span className="font-num text-title tabular-nums text-ink">{streak}</span>
      </span>

      <span className="inline-flex items-center gap-2 rounded-full border border-stroke bg-surface px-3 py-2">
        <span className="text-attn">
          <StarFilledIcon size={18} />
        </span>
        <span className="font-num text-title tabular-nums text-ink">
          {points.toLocaleString('ru-RU')}
        </span>
      </span>
    </div>
  )
}
