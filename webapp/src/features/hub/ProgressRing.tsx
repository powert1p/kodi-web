import type { CSSProperties } from 'react'
import type { TaskState } from '../../lib/types'
import { STATE_META } from './stateConfig'

interface ProgressRingProps {
  /** Всего задач в срезе. */
  total: number
  /** Сколько уже «готово» (доля закрытых). */
  done: number
  /** Самое приоритетное состояние дня — задаёт цвет дуги. */
  leadState: TaskState
}

// SIGNATURE: «глиняная» прогресс-баранка. Внешнее надутое кольцо (clay) с утопленным
// треком (clay-inset) и яркой дугой; в центре — утопленный колодец с крупным табличным
// счётчиком (M PLUS Rounded Black). Цвет дуги кодирует приоритетное состояние дня.
const SIZE = 120
const STROKE = 13
const R = (SIZE - STROKE) / 2 - 4
const C = 2 * Math.PI * R

export function ProgressRing({ total, done, leadState }: ProgressRingProps) {
  // Минимальная видимая дуга, чтобы кольцо не выглядело «пустым» при 0 закрытых.
  const ratio = total > 0 ? Math.min(done / total, 1) : 0
  const shown = Math.max(ratio, 0.06)
  const dash = C * shown
  const accent = STATE_META[leadState].accentVar
  const remaining = Math.max(total - done, 0)

  return (
    <div
      className="clay relative grid shrink-0 place-items-center rounded-full"
      style={{ width: SIZE, height: SIZE, '--c': accent } as CSSProperties}
    >
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="absolute inset-0 size-full -rotate-90"
        role="img"
        aria-label={`Закрыто ${done} из ${total}`}
      >
        {/* Утопленный трек */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          fill="none"
          stroke="color-mix(in oklab, var(--color-brand) 9%, var(--color-surface-muted))"
          strokeWidth={STROKE}
        />
        {/* Яркая надутая дуга с круглой шапкой */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          fill="none"
          stroke="var(--c)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${C}`}
          className="transition-[stroke-dasharray] duration-700 ease-out motion-reduce:transition-none"
        />
      </svg>
      {/* Утопленный центральный колодец со счётчиком */}
      <div className="clay-inset relative z-10 grid size-[74px] place-items-center rounded-full">
        <span className="font-num text-[2rem] font-black leading-none text-ink tabular-nums">
          {remaining}
        </span>
        <span className="-mt-0.5 text-[0.58rem] font-extrabold uppercase tracking-wider text-ink-mute">
          осталось
        </span>
      </div>
    </div>
  )
}
