import { Mascot } from '../../components/Mascot'
import { ProgressBar } from './ProgressBar'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
}

// Hero среза = AiPlus ApInformer (warning): тёплая подложка bg-light-brand-warning + бордер
// stroke-brand-light выделяют ЕДИНСТВЕННЫЙ фокус экрана из ряда белых карточек ниже.
// Маскот «Кёди», eyebrow, крупный счётчик-заголовок (h2), growth-копия, полоса прогресса.
export function HubHero({ total, done }: HubHeroProps) {
  const remaining = Math.max(total - done, 0)
  const allDone = remaining === 0

  const title = allDone ? 'Всё разобрано!' : `${remaining} ${plural(remaining)}`
  const line = allDone
    ? 'Ни одной незакрытой ошибки — чисто. Можно закреплять победы.'
    : 'Каждая разобранная ошибка — место, где мозг стал сильнее. Начнём с первой.'

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-stroke-brand-light bg-bg-light-brand-warning p-4">
      <div className="flex items-center gap-3">
        <Mascot mood={allDone ? 'celebrate' : 'cheer'} size={56} className="shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-caption1-medium uppercase tracking-[0.08em] text-text-brand">
            Срез на сегодня
          </p>
          <h1 className="text-h2 text-text-primary">{title}</h1>
        </div>
      </div>

      <p className="text-caption1 text-text-dark-gray">{line}</p>

      <ProgressBar done={done} total={total} />
    </section>
  )
}

// Склонение «ошибка» для русского счётчика (с глаголом «ждёт/ждут»).
function plural(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'ошибка ждёт'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'ошибки ждут'
  return 'ошибок ждут'
}
