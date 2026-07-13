import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { KodiBubble } from '../../components/KodiBubble'
import { RightIcon } from '../../icons'
import { ProgressBar } from './ProgressBar'
import heroDesk from '../../assets/hero-desk.jpg'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
  /** id самой приоритетной ошибки — цель единственного primary-CTA экрана. */
  firstTaskId: string | null
}

// Трейлхед маршрута (стоп 0 RouteSpine): тёплая полоса-иллюстрация мастерской со
// сплошным scrim (AA §10), эйбров, ЧИСЛО-ГЕРОЙ (Unbounded-гигант) прямо на маршруте
// (§1: «12» стоит НА кривой), голос Кёди (hi §7), честный прогресс и ЕДИНСТВЕННЫЙ
// primary-CTA «Разобрать первую» — виден без скролла (§1).
export function HubHero({ total, done, firstTaskId }: HubHeroProps) {
  const navigate = useNavigate()
  const remaining = Math.max(total - done, 0)
  const allDone = remaining === 0

  return (
    <section className="relative -mt-1 overflow-hidden rounded-card border border-stroke">
      {/* Иллюстрация мастерской + сплошной тёплый scrim под текстом (AA) */}
      <img
        src={heroDesk}
        alt=""
        aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-90"
      />
      <div className="hero-scrim pointer-events-none absolute inset-0" />

      <div className="relative flex flex-col gap-4 p-4">
        <p className="text-caption1-medium uppercase tracking-[0.14em] text-brand-ink">
          Срез на сегодня
        </p>

        {allDone ? (
          <h1 className="text-h1 text-ink">Всё разобрано!</h1>
        ) : (
          <h1 className="flex items-end gap-3">
            <span className="text-hero text-ink">{remaining}</span>
            <span className="text-h1 pb-2 text-ink">{plural(remaining)}</span>
          </h1>
        )}

        <KodiBubble mood={allDone ? 'celebrate' : 'hi'} size="s">
          {allDone
            ? 'Ни одной незакрытой ошибки — чисто. Можно закреплять победы.'
            : 'Привет! Я рядом. Начнём с первой — она сегодня главная, дальше будет легче.'}
        </KodiBubble>

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
      </div>
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
