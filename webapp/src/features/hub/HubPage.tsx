import { useEffect, useRef } from 'react'
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

  const tasks = data
    ? [...data.tasks].sort((a, b) => STATE_PRIORITY.indexOf(a.state) - STATE_PRIORITY.indexOf(b.state))
    : []
  const showConsent = !!profile && profile.photo_consent === null && !isConsentDismissed()

  if (isPending) return <HubSkeleton />
  if (isError) {
    return <div className="mx-auto flex min-h-[70dvh] max-w-3xl items-center px-5"><HubError onRetry={() => void refetch()} /></div>
  }
  if (tasks.length === 0) {
    return (
      <div className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-5xl flex-col justify-center gap-5 px-5 py-10">
        <HubEmpty hasActivity={data?.has_activity ?? false} />
        {showConsent && <ConsentCard variant="hub" />}
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-paper text-text">
      <HubHero tasks={tasks} />
      <div className="mx-auto grid max-w-[90rem] items-start gap-10 px-5 py-12 md:px-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:py-16">
        <section aria-labelledby="review-queue-title" className="min-w-0">
          <div className="flex items-end justify-between gap-5 border-b border-ink/20 pb-5">
            <div>
              <p className="text-mark text-brand-deep">После главного</p>
              <h2 id="review-queue-title" className="mt-3 text-h2 text-ink">Что ещё можно подтянуть</h2>
            </div>
            <p className="hidden max-w-[15rem] text-right text-caption1 text-muted sm:block">
              Статус — это уверенность, а не оценка.
            </p>
          </div>
          <ol>
            {tasks.slice(1).map((task, index) => (
              <li key={task.id}><TaskCard task={task} index={index + 2} /></li>
            ))}
          </ol>
          {tasks.length === 1 && (
            <p className="mt-5 rounded-control bg-sage-soft px-4 py-4 text-body text-text">
              Это единственная задача в текущем списке. После неё останется коротко закрепить результат.
            </p>
          )}
        </section>
        <aside className="flex flex-col gap-6 lg:sticky lg:top-6">
          {showConsent && <ConsentCard delay={70} variant="hub" />}
          <ProblemTopicsCard delay={120} />
        </aside>
      </div>
    </div>
  )
}
