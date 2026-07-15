import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { Mascot } from '../../components/Mascot'
import { MathText } from '../../components/MathText'
import { RightIcon } from '../../icons'
import type { WrongTask } from '../../lib/types'
import { StateChip } from './StateChip'

interface HubHeroProps { tasks: readonly WrongTask[] }

export function HubHero({ tasks }: HubHeroProps) {
  const navigate = useNavigate()
  const first = tasks[0] ?? null
  if (!first) return null

  const route = tasks.slice(0, 4)

  return (
    <section aria-labelledby="review-focus-title">
      <div className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-[90rem] items-center gap-6 px-5 py-5 md:px-8 lg:grid-cols-[minmax(15rem,0.72fr)_minmax(26rem,1.15fr)_minmax(12rem,0.46fr)] lg:gap-10 lg:py-12">
        <div className="order-2 min-w-0 lg:order-none">
          <p className="text-mark text-brand-deep">Твой короткий маршрут</p>
          <h1 id="review-focus-title" className="mt-3 max-w-xl text-[clamp(32px,4.5vw,52px)] font-bold leading-[1] tracking-[-0.055em] text-ink">
            Один момент — и дальше легче.
          </h1>
          <p className="mt-4 max-w-sm text-body text-muted">
            Вернёмся к месту, где решение свернуло не туда. Остальное уже получается.
          </p>
        </div>

        <article className="tape-card tape-card--notched order-1 relative min-w-0 px-5 py-5 pl-14 md:px-8 md:py-7 md:pl-20 lg:order-none">
          <RouteRail tasks={route} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-mark text-brand-deep">Сейчас · {first.topic_label}</p>
            <StateChip state={first.state} />
          </div>

          <div className="math-prose mt-5 pb-2 md:mt-6">
            <p className="formula-body max-w-4xl text-[clamp(30px,5vw,48px)] font-bold leading-[1.08] tracking-[-0.045em] text-ink">
              <MathText text={first.statement} />
            </p>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-ink/10 pt-4">
            <p className="text-caption1 text-muted">
              В прошлый раз: <span className="font-num font-semibold text-oxide">{first.wrong_answer}</span>
            </p>
            <p className="text-caption1-medium text-ink">разбор по шагам</p>
          </div>

          <ApButton full size="l" onClick={() => navigate(`/drill/${first.id}`)} className="mt-5 justify-between px-5">
            Разобрать точный шаг <RightIcon size={18} />
          </ApButton>
          <p className="mt-4 text-caption2 text-muted">Следом — короткая проверка на другой задаче.</p>
        </article>

        <aside className="order-3 flex items-end gap-3 rounded-card border border-ink/10 bg-sage-soft/55 px-4 pt-3 lg:order-none lg:block lg:px-4 lg:pt-4 lg:pb-4">
          <Mascot mood="hi" size="l" eager decorative className="mascot-shadow w-28 shrink-0 lg:w-full" />
          <p className="mb-3 max-w-xs text-caption1 text-muted lg:mt-2 lg:mb-0">
            <span className="font-semibold text-ink">Кёди держит контекст.</span><br />Ответ не скажет — следующий шаг подхватит.
          </p>
        </aside>
      </div>
    </section>
  )
}

function RouteRail({ tasks }: { tasks: readonly WrongTask[] }) {
  return (
    <ol className="hub-route-rail absolute top-5 bottom-5 left-4 flex w-7 flex-col items-center justify-between md:left-7" aria-label="Очередь разборов">
      {tasks.map((task, index) => (
        <li
          key={task.id}
          className={[
                'font-display grid size-7 place-items-center rounded-full border text-caption2 font-bold',
            index === 0
              ? 'border-brand bg-brand text-ink ring-4 ring-brand-soft'
              : 'border-stroke bg-surface text-muted',
          ].join(' ')}
        >
          <span aria-hidden>{index + 1}</span>
          <span className="sr-only">{task.topic_label}: {index === 0 ? 'текущий разбор' : 'впереди'}</span>
        </li>
      ))}
    </ol>
  )
}
