import { Mascot } from '../../components/Mascot'
import { ProgressBar } from './ProgressBar'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
}

// Приветствие с маскотом «Кёди»: speech-строка в духе growth-mindset,
// краткая сводка среза + большая полоса прогресса. Чистая плоская карточка —
// тактильная глубина приберегается для 3D-кнопок «Разобрать».
export function HubHero({ total, done }: HubHeroProps) {
  const remaining = Math.max(total - done, 0)
  const line =
    remaining === 0
      ? 'Ни одной незакрытой ошибки — чисто!'
      : `Сегодня ${remaining} ${plural(remaining)}. Каждая делает мозг сильнее — разберём вместе!`

  return (
    <section className="card-flat flex flex-col gap-4 rounded-(--radius-card) p-4">
      <div className="flex items-start gap-3">
        <Mascot mood="cheer" size={68} className="-mt-1 shrink-0" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-[0.66rem] font-extrabold uppercase tracking-[0.16em] text-primary-ink">
            Срез на сегодня
          </span>
          <h1 className="font-display text-[1.6rem] font-black leading-[1.05] tracking-tight text-ink">
            Привет!
          </h1>
          {/* Speech-строка маскота */}
          <p className="text-sm font-bold leading-snug text-ink">{line}</p>
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
