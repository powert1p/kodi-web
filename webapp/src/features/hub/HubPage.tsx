import type { CSSProperties } from 'react'
import { useWrongTasks } from './useWrongTasks'
import { TaskCard } from './TaskCard'
import { HubSkeleton } from './HubSkeleton'
import { HubEmpty } from './HubEmpty'
import { HubError } from './HubError'

// Hub — «срез» ошибок. Главный экран: триаж задач как тренировочные репы.
export function HubPage() {
  const { data, isPending, isError, refetch } = useWrongTasks()

  const count = data?.length ?? 0
  const revisit = data?.filter((t) => t.state === 'revisit').length ?? 0

  return (
    <div className="flex flex-col gap-6">
      {/* Hero-заголовок: эвербрау + крупный display + счётчик */}
      <header className="reveal flex flex-col gap-3 pt-1">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">
          Режим тренировки
        </span>
        <h1 className="font-display text-[2.65rem] font-extrabold leading-[0.95] tracking-tight text-ink">
          Над
          <br />
          ошибками
        </h1>

        {!isPending && !isError && count > 0 && (
          <div className="flex items-center gap-2 pt-1">
            <span
              className="font-num text-base font-bold text-ink"
              style={{ '--c': 'var(--color-revisit)' } as CSSProperties}
            >
              {count}
            </span>
            <span className="text-sm text-ink-mute">
              {count === 1 ? 'задача в срезе' : 'задач в срезе'}
              {revisit > 0 && (
                <>
                  {' · '}
                  <span className="font-semibold text-revisit">
                    {revisit} ждут разбора
                  </span>
                </>
              )}
            </span>
          </div>
        )}
      </header>

      {/* Состояния */}
      {isPending && <HubSkeleton />}
      {isError && <HubError onRetry={() => void refetch()} />}
      {!isPending && !isError && count === 0 && <HubEmpty />}

      {!isPending && !isError && count > 0 && (
        <ul className="flex flex-col gap-3">
          {data!.map((task, i) => (
            <li key={task.id}>
              <TaskCard task={task} index={i + 1} delay={120 + i * 70} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
