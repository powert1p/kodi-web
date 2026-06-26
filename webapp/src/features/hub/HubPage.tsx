import type { CSSProperties } from 'react'
import { useWrongTasks } from './useWrongTasks'
import { StatusRow } from './StatusRow'
import { HubHero } from './HubHero'
import { TaskCard } from './TaskCard'
import { HubSkeleton } from './HubSkeleton'
import { HubEmpty } from './HubEmpty'
import { HubError } from './HubError'
import { STATE_PRIORITY } from './stateConfig'

// Hub — «срез» ошибок. Главный экран: статус-строка геймификации (streak + XP),
// приветствие маскота с полосой прогресса, затем плоские плитки-ошибки,
// отсортированные по приоритету разбора. Каждое действие — чанковая 3D-кнопка.
//
// Геймификация: streak/points — заглушка до соответствующего эндпоинта
// (на сегодня показываем демо-значения; форму подключим позже).
const STREAK = 5
const POINTS = 1280

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

  return (
    <div className="flex flex-col gap-4">
      {isPending && <HubSkeleton />}
      {isError && <HubError onRetry={() => void refetch()} />}
      {!isPending && !isError && total === 0 && <HubEmpty />}

      {!isPending && !isError && total > 0 && (
        <>
          <div
            className="reveal"
            style={{ '--reveal-delay': '0ms' } as CSSProperties}
          >
            <StatusRow streak={STREAK} points={POINTS} />
          </div>

          <div
            className="reveal"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <HubHero total={total} done={done} />
          </div>

          <div
            className="reveal flex items-baseline justify-between px-1 pt-1"
            style={{ '--reveal-delay': '120ms' } as CSSProperties}
          >
            <h2 className="font-display text-lg font-extrabold text-ink">
              Твои ошибки
            </h2>
            <span className="font-num text-sm font-extrabold tabular-nums text-ink-mute">
              {total}
            </span>
          </div>

          <ul className="flex flex-col gap-3">
            {tasks.map((task, i) => (
              <li key={task.id}>
                <TaskCard task={task} delay={170 + i * 60} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
