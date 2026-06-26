import type { CSSProperties } from 'react'
import { useWrongTasks } from './useWrongTasks'
import { HubHero } from './HubHero'
import { TaskCard } from './TaskCard'
import { HubSkeleton } from './HubSkeleton'
import { HubEmpty } from './HubEmpty'
import { HubError } from './HubError'
import { STATE_PRIORITY } from './stateConfig'
import type { TaskState } from '../../lib/types'

// Hub — «срез» ошибок. Главный экран: тёплое приветствие + hero-кольцо прогресса,
// затем глиняные плитки-ошибки, отсортированные по приоритету разбора.
export function HubPage() {
  const { data, isPending, isError, refetch } = useWrongTasks()

  // Триаж: сначала «разберём», потом «почти», потом «готово».
  const tasks = data
    ? [...data].sort(
        (a, b) =>
          STATE_PRIORITY.indexOf(a.state) - STATE_PRIORITY.indexOf(b.state),
      )
    : []

  const total = tasks.length
  const done = tasks.filter((t) => t.state === 'got').length
  const leadState: TaskState = tasks[0]?.state ?? 'revisit'

  return (
    <div className="flex flex-col gap-5">
      {isPending && <HubSkeleton />}
      {isError && <HubError onRetry={() => void refetch()} />}
      {!isPending && !isError && total === 0 && <HubEmpty />}

      {!isPending && !isError && total > 0 && (
        <>
          <HubHero total={total} done={done} leadState={leadState} />

          <div
            className="reveal flex items-baseline justify-between px-1"
            style={{ '--reveal-delay': '90ms' } as CSSProperties}
          >
            <h2 className="font-display text-lg font-extrabold text-ink">
              Твои ошибки
            </h2>
            <span className="font-num text-sm font-extrabold text-ink-soft tabular-nums">
              {total}
            </span>
          </div>

          <ul className="flex flex-col gap-3.5">
            {tasks.map((task, i) => (
              <li key={task.id}>
                <TaskCard task={task} delay={150 + i * 60} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
