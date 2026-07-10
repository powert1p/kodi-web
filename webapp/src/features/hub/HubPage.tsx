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

// Hub — «срез» ошибок. Главный экран: hero с ЕДИНСТВЕННЫМ primary-CTA
// «Разобрать первую», затем плоские плитки-ошибки, отсортированные по
// приоритету разбора (сами тапаются, без кнопки-дубля). Стрик/очки не
// показываем — реального источника в API пока нет (§1f ТЗ: реальные или ничего).

export function HubPage() {
  const { data, isPending, isError, refetch } = useWrongTasks()
  const { data: profile } = useMe()

  // Телеметрия открытия hub — один раз за монтирование (ref-guard от повторов при ре-рендере).
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
        (a, b) =>
          STATE_PRIORITY.indexOf(a.state) - STATE_PRIORITY.indexOf(b.state),
      )
    : []

  const total = tasks.length
  const done = tasks.filter((t) => t.state === 'got').length
  // Новичок (has_activity=false) vs ветеран (true) — разводит пустой hub.
  const hasActivity = data?.has_activity ?? false

  // Согласие ещё не спрошено (null — родитель пока не ответил) и не отложено в этой сессии.
  const showConsent = !!profile && profile.photo_consent === null && !isConsentDismissed()

  return (
    <div className="flex flex-col gap-4">
      {isPending && <HubSkeleton />}
      {isError && <HubError onRetry={() => void refetch()} />}

      {!isPending && !isError && total === 0 && (
        // Пустой hub центрируем по вертикали в области над нижним баром — карточка-
        // приглашение как единственный фокус, без мёртвой нижней половины (§2.8).
        // min-h в dvh (не %) — надёжно резолвится от вьюпорта, не зависит от высоты main.
        <div className="flex min-h-[72dvh] flex-col justify-center gap-4">
          {showConsent && <ConsentCard delay={0} variant="hub" />}
          <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
            <HubEmpty hasActivity={hasActivity} />
          </div>
        </div>
      )}

      {!isPending && !isError && total > 0 && (
        <>
          {showConsent && <ConsentCard delay={0} variant="hub" />}

          <div
            className="reveal"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <HubHero total={total} done={done} firstTaskId={tasks[0]?.id ?? null} />
          </div>

          <ProblemTopicsCard delay={160} />

          <div
            className="reveal flex items-center gap-2 px-0.5 pt-1"
            style={{ '--reveal-delay': '180ms' } as CSSProperties}
          >
            <h2 className="text-h3 text-ink">Твои ошибки</h2>
            <span className="font-num inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-surface px-1 text-caption2-medium tabular-nums text-text">
              {total}
            </span>
            <span className="ml-auto text-caption1 text-muted">сложные сверху</span>
          </div>

          <ul className="flex flex-col gap-3">
            {tasks.map((task, i) => (
              <li key={task.id}>
                <TaskCard task={task} delay={230 + i * 60} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
