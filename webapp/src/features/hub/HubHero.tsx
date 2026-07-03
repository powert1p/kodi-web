import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'
import { RightIcon } from '../../icons'
import { ProgressBar } from './ProgressBar'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
  /** id самой приоритетной ошибки — цель единственного primary-CTA экрана. */
  firstTaskId: string | null
}

// Hero среза = ApCard tone=brand-soft — ЕДИНСТВЕННЫЙ активный фокус экрана (canon §1/§4):
// маскот «Кёди», eyebrow, крупный счётчик-заголовок (h1), growth-копия, полоса прогресса
// и ЕДИНСТВЕННЫЙ primary-CTA экрана «Разобрать первую» (canon §4 — одно главное действие,
// без него срез начинался только с текст-ссылок в плитках ниже — audit-дефект).
export function HubHero({ total, done, firstTaskId }: HubHeroProps) {
  const navigate = useNavigate()
  const remaining = Math.max(total - done, 0)
  const allDone = remaining === 0

  const title = allDone ? 'Всё разобрано!' : `${remaining} ${plural(remaining)}`
  const line = allDone
    ? 'Ни одной незакрытой ошибки — чисто. Можно закреплять победы.'
    : 'Каждая разобранная ошибка — место, где мозг стал сильнее. Начнём с первой.'

  return (
    <ApCard as="section" tone="brand-soft" padding="m" className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Mascot mood={allDone ? 'celebrate' : 'hi'} size="m" className="shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-caption1-medium uppercase tracking-[0.08em] text-brand">
            Срез на сегодня
          </p>
          <h1 className="text-h2 text-ink">{title}</h1>
        </div>
      </div>

      <p className="text-caption1 text-text">{line}</p>

      <ProgressBar done={done} total={total} />

      {!allDone && firstTaskId && (
        <ApButton
          variant="primary"
          size="l"
          full
          onClick={() => navigate(`/drill/${firstTaskId}`)}
        >
          Разобрать первую
          <RightIcon size={18} />
        </ApButton>
      )}
    </ApCard>
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
