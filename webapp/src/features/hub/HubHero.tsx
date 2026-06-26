import type { TaskState } from '../../lib/types'
import { ProgressRing } from './ProgressRing'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
  /** Приоритетное состояние — цвет дуги кольца. */
  leadState: TaskState
}

// Hero-панель «срез на сегодня»: тёплое приветствие + ободряющая строка (growth-mindset)
// слева, прогресс-кольцо (signature) справа — off-axis, не центрированный «большой счётчик».
export function HubHero({ total, done, leadState }: HubHeroProps) {
  const remaining = Math.max(total - done, 0)
  const line =
    remaining === 0
      ? 'Ни одной незакрытой ошибки — чисто.'
      : remaining === 1
        ? 'Одна ошибка ждёт — разберём за пару минут.'
        : `${remaining} ${plural(remaining)} ждут — каждая делает мозг сильнее.`

  return (
    <section className="clay reveal flex items-center gap-3 rounded-(--radius-card) p-5">
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className="text-[0.7rem] font-extrabold uppercase tracking-[0.18em] text-brand">
          Срез на сегодня
        </span>
        <h1 className="font-display text-[2.05rem] font-black leading-[0.98] tracking-tight text-ink">
          Привет!
        </h1>
        <p className="text-sm font-bold leading-snug text-ink-soft">{line}</p>
      </div>
      <ProgressRing total={total} done={done} leadState={leadState} />
    </section>
  )
}

// Склонение «ошибка» для русского счётчика.
function plural(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'ошибка'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'ошибки'
  return 'ошибок'
}
