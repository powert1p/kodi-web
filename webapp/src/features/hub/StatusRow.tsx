import { HistoryIcon, StarFilledIcon } from '../../icons'

interface StatusRowProps {
  /** Дни подряд (streak). */
  streak: number
  /** Накопленные очки/XP. */
  points: number
}

// Верхняя статус-строка: streak (часы) + XP (звезда). Плоские пилюли AiPlus —
// фон bg-tertiary, 1px stroke-secondary, радиус full. Табличные цифры.
// Иконки из набора AiPlus, тонированы брендом/жёлтым через currentColor.
export function StatusRow({ streak, points }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-stroke-secondary bg-bg-tertiary px-3 py-1.5">
        <span className="text-text-brand">
          <HistoryIcon size={18} />
        </span>
        <span className="font-num text-title tabular-nums text-text-primary">
          {streak}
        </span>
      </span>

      <span className="inline-flex items-center gap-1.5 rounded-full border border-stroke-secondary bg-bg-tertiary px-3 py-1.5">
        <span className="text-text-yellow">
          <StarFilledIcon size={18} />
        </span>
        <span className="font-num text-title tabular-nums text-text-primary">
          {points.toLocaleString('ru-RU')}
        </span>
      </span>
    </div>
  )
}
