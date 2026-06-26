import { Mascot } from '../../components/Mascot'
import { ProgressBar } from './ProgressBar'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
}

// Приветствие с маскотом «Кёди»: speech-строка growth-mindset, краткая сводка
// среза + полоса прогресса. Плоская карточка AiPlus (ap-card, 1px-бордер, без тени).
export function HubHero({ total, done }: HubHeroProps) {
  const remaining = Math.max(total - done, 0)
  const line =
    remaining === 0
      ? 'Ни одной незакрытой ошибки — чисто!'
      : `Сегодня ${remaining} ${plural(remaining)}. Каждая делает мозг сильнее — разберём вместе!`

  return (
    <section className="ap-card flex flex-col gap-4 p-4">
      <div className="flex items-start gap-3">
        <Mascot mood="cheer" size={64} className="-mt-1 shrink-0" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-caption1-medium uppercase tracking-[0.12em] text-text-brand">
            Срез на сегодня
          </span>
          <h1 className="text-h2 text-text-primary">Привет!</h1>
          <p className="text-caption1 text-text-primary">{line}</p>
        </div>
      </div>

      <ProgressBar done={done} total={total} />
    </section>
  )
}

// Склонение «ошибка» для русского счётчика.
function plural(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'ошибка ждёт'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'ошибки ждут'
  return 'ошибок ждут'
}
