import { useEffect, useRef, type CSSProperties } from 'react'
import { useWrongTasks } from './useWrongTasks'
import { track } from '../../lib/telemetry'
import { HubHero } from './HubHero'
import { ProblemTopicsCard } from './ProblemTopicsCard'
import { TaskCard } from './TaskCard'
import { HubSkeleton } from './HubSkeleton'
import { HubEmpty } from './HubEmpty'
import { HubError } from './HubError'
import { ConsentCard, isConsentDismissed } from './ConsentCard'
import { useMe } from '../auth/useMe'
import { STATE_PRIORITY } from './stateConfig'
import { RouteSpine, type RouteStop } from '../../components/route/RouteSpine'

// Hub — «срез» ошибок. Signature-маршрут ведёт от ЧИСЛА-ГЕРОЯ (hero-трейлхед стоит
// НА кривой, §1) вниз через каждую ошибку честной отметкой до флажка-вершины (§2).
// Ведущая ошибка — current (пульс), CTA «Разобрать первую» в hero без скролла.
export function HubPage() {
  const { data, isPending, isError, refetch } = useWrongTasks()
  const { data: profile } = useMe()

  const openTrackedRef = useRef(false)
  useEffect(() => {
    if (!openTrackedRef.current) {
      openTrackedRef.current = true
      void track('hub_opened')
    }
  }, [])

  // Триаж: сначала «разберём», потом «почти», потом «готово».
  const tasks = data
    ? [...data.tasks].sort(
        (a, b) => STATE_PRIORITY.indexOf(a.state) - STATE_PRIORITY.indexOf(b.state),
      )
    : []

  const total = tasks.length
  const done = tasks.filter((t) => t.state === 'got').length
  const hasActivity = data?.has_activity ?? false
  const showConsent = !!profile && profile.photo_consent === null && !isConsentDismissed()

  // Стопы маршрута списка: каждая ошибка честной отметкой (первая = current, ты здесь) →
  // флажок-вершина. Трейлхед-число живёт в HubHero выше и запускает штрих, который
  // стыкуется с рельсом списка (тот же x=22) — маршрут читается как единая линия (R3 §1).
  const stops: RouteStop[] =
    total > 0
      ? [
          ...tasks.map<RouteStop>((task, i) => ({
            key: task.id,
            state: i === 0 ? 'current' : 'todo',
            label: String(i + 1),
            content: <TaskCard task={task} lead={i === 0} />,
          })),
          {
            key: 'summit',
            state: 'flag',
            content: (
              <div className="flex min-h-8 items-center">
                <span className="font-display text-caption1-medium text-brand-ink">
                  Вершина дня: весь срез разобран
                </span>
              </div>
            ),
          },
        ]
      : []

  return (
    <div className="flex flex-col gap-4">
      {isPending && <HubSkeleton />}
      {isError && <HubError onRetry={() => void refetch()} />}

      {!isPending && !isError && total === 0 && (
        <div className="flex min-h-[72dvh] flex-col justify-center gap-4">
          {showConsent && <ConsentCard delay={0} variant="hub" />}
          <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
            <HubEmpty hasActivity={hasActivity} />
          </div>
        </div>
      )}

      {!isPending && !isError && total > 0 && (
        <>
          {/* Трейлхед: число-герой запускает штрих маршрута (первый вьюпорт, §1) */}
          <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
            <HubHero total={total} done={done} firstTaskId={tasks[0]?.id ?? null} />
          </div>

          <div
            className="reveal flex items-center gap-2 px-0.5"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <h2 className="font-display text-caption1-medium uppercase tracking-[0.12em] text-label">
              Сегодняшний маршрут
            </h2>
            <span className="ml-auto text-caption1 text-muted">сначала трудные</span>
          </div>

          <div className="reveal" style={{ '--reveal-delay': '100ms' } as CSSProperties}>
            <RouteSpine stops={stops} currentIndex={0} ariaLabel={`Маршрут из ${total} ошибок`} />
          </div>

          {/* Согласие — мягкий нудж ПОСЛЕ маршрута: hero+CTA держат первый вьюпорт (§1). */}
          {showConsent && <ConsentCard delay={0} variant="hub" />}

          <ProblemTopicsCard delay={160} />
        </>
      )}
    </div>
  )
}
