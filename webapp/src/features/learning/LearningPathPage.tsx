import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { fetchLearningPath, learningIdentity } from '../../lib/api'
import type { LearningPathLesson, LearningPathSummary } from '../../lib/types'
import { useAuth } from '../auth/AuthContext'

const LEARNING_PHASES = [
  ['01', 'Разобрать', 'Увидеть неизменную часть', 'worked'],
  ['02', 'Доделать', 'Снять опоры по шагам', 'guided'],
  ['03', 'Решить', 'Проверить себя без опор', 'independent'],
  ['04', 'Перенести', 'Применить метод в новой ситуации', 'transfer'],
] as const

export function LearningPathPage() {
  const { token } = useAuth()
  const identity = learningIdentity(token)
  const query = useQuery({
    queryKey: ['learning-path', identity],
    queryFn: ({ signal }) => fetchLearningPath(signal),
    staleTime: 0,
    gcTime: 0,
    retry: 1,
  })

  if (query.isPending) return <LearningPathLoading />
  if (query.isError) return <LearningPathError onRetry={() => void query.refetch()} />
  if (!query.data.lesson) return <LearningPathEmpty path={query.data.path} />
  return <LearningPathView path={query.data.path} lesson={query.data.lesson} />
}

export function LearningPathView({
  path,
  lesson,
}: {
  path: LearningPathSummary
  lesson: LearningPathLesson
}) {
  const navigate = useNavigate()
  const started = lesson.status !== 'not_started'
  const currentPhaseIndex = LEARNING_PHASES.findIndex(([, , , role]) => (
    role === lesson.progress.current_role
  ))
  const lessonProgress = lesson.status === 'completed'
    ? 'Результат сохранён'
    : started
      ? `${lesson.progress.completed} из ${lesson.progress.total} шагов сохранено`
      : 'От примера к самостоятельному решению'
  const blockProgress = `В этом блоке: ${path.current_block.completed_lessons} из ${path.current_block.total_lessons} ${blockLessonWord(path.current_block.total_lessons)}`

  return (
    <div className="mx-auto grid min-h-[calc(100dvh-9rem)] max-w-[90rem] items-center gap-9 px-5 py-7 md:px-8 lg:grid-cols-[minmax(0,0.94fr)_minmax(30rem,0.78fr)] lg:gap-16 lg:py-11">
      <section className="min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-mark text-brand-deep">Мой путь</p>
          <span className="rounded-chip border border-ink/10 bg-surface/70 px-3 py-2 text-caption2-medium text-muted">
            {path.title}
          </span>
        </div>

        <p className="mt-7 text-caption1-medium text-brand-deep">
          Текущий блок · {path.current_block.title}
        </p>
        <h1 className="mt-3 max-w-3xl text-hero text-ink">{path.current_block.title}</h1>
        <p className="mt-3 text-caption1-medium text-muted">{blockProgress}</p>

        <div className="mt-7 max-w-2xl border-l-2 border-brand bg-surface/55 px-5 py-5 md:px-6">
          <p className="text-mark text-brand-deep">
            {lesson.status === 'completed' ? 'Освоенный урок' : started ? 'Продолжить урок' : 'Следующий урок'}
          </p>
          <h2 className="mt-3 text-h2 text-ink">{lesson.lesson_title}</h2>
          <p className="mt-3 max-w-xl text-body text-text">{lesson.goal}</p>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-caption1-medium text-muted">
            <span>≈ {lesson.duration_minutes} минут</span>
            <span>{lessonProgress}</span>
          </div>
          <div className="mt-6 max-w-sm">
            <ApButton
              size="l"
              full
              onClick={() => navigate(`/lesson/${lesson.primary_action.lesson_id}`)}
            >
              {lesson.primary_action.label}
            </ApButton>
          </div>
        </div>
      </section>

      <section className="tape-stage min-w-0 px-5 py-6 md:px-8 md:py-8" aria-labelledby="learning-route-title">
        <div className="border-b border-ink/10 pb-5">
          <p className="text-mark text-brand-deep">Как растёт навык</p>
          <h2 id="learning-route-title" className="mt-2 text-h3 text-ink">От примера к переносу</h2>
        </div>
        <ol className="mt-2 divide-y divide-ink/10">
          {LEARNING_PHASES.map(([number, label, detail], index) => {
            const done = lesson.status === 'completed' || currentPhaseIndex > index
            const active = lesson.status !== 'completed' && currentPhaseIndex === index
            return (
              <li
                key={number}
                aria-current={active ? 'step' : undefined}
                className="grid grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 py-4"
              >
                <span
                  className={[
                    'grid h-10 w-10 place-items-center rounded-full font-display text-caption1-medium',
                    done
                      ? 'bg-success text-surface'
                      : active
                        ? 'bg-brand text-ink shadow-[0_0_0_5px_var(--brand-soft)]'
                        : 'border border-stroke bg-paper text-muted',
                  ].join(' ')}
                  aria-hidden
                >
                  {done ? '✓' : number}
                </span>
                <span className="min-w-0">
                  <span className="block text-title text-ink">{label}</span>
                  <span className="mt-0.5 block text-caption1 text-muted">{detail}</span>
                </span>
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}

function blockLessonWord(total: number) {
  return total % 10 === 1 && total % 100 !== 11 ? 'урока' : 'уроков'
}

function LearningPathLoading() {
  return (
    <div className="mx-auto grid min-h-[calc(100dvh-9rem)] max-w-[90rem] items-center gap-9 px-5 py-8 md:px-8 lg:grid-cols-2" role="status" aria-label="Загружаем учебный путь">
      <div>
        <div className="shimmer h-3 w-32 rounded-chip bg-paper-2" />
        <div className="shimmer mt-5 h-16 w-4/5 rounded-control bg-paper-2" />
        <div className="shimmer mt-4 h-40 w-full max-w-xl rounded-control bg-paper-2" />
      </div>
      <div className="tape-stage min-h-96 p-7">
        <div className="shimmer h-full rounded-control bg-paper-2" />
      </div>
    </div>
  )
}

function LearningPathError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-2xl items-center px-5 py-10">
      <section role="alert" className="tape-stage w-full px-6 py-8 md:px-9">
        <p className="text-mark text-oxide">Не удалось загрузить путь</p>
        <h1 className="mt-3 text-h2 text-ink">Твой прогресс никуда не пропал</h1>
        <p className="mt-4 text-body text-muted">Проверь соединение и попробуй открыть текущий блок ещё раз.</p>
        <div className="mt-6"><ApButton onClick={onRetry}>Попробовать снова</ApButton></div>
      </section>
    </div>
  )
}

function LearningPathEmpty({ path }: { path: LearningPathSummary }) {
  return (
    <div className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-2xl items-center px-5 py-10">
      <section className="tape-stage w-full px-6 py-8 md:px-9">
        <p className="text-mark text-brand-deep">Мой путь · {path.title}</p>
        <h1 className="mt-3 text-h2 text-ink">Маршрут ещё не собран</h1>
        <p className="mt-4 text-body text-muted">Когда в текущем блоке появится первый урок, здесь будет один понятный следующий шаг.</p>
      </section>
    </div>
  )
}
