import { useRef, type ReactNode } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { FocusTopbar } from '../../components/FocusTopbar'
import { ApButton } from '../../components/ApButton'
import { VerificationCard } from './VerificationCard'
import { ClosureCelebration } from './ClosureCelebration'
import { useClosure } from './useClosure'
import { useWrongTask } from '../../lib/api'

export function ClosurePage() {
  const location = useLocation()
  const { taskId } = useParams<{ taskId: string }>()
  const { data: task, isLoading: isTaskLoading } = useWrongTask(taskId ?? '')
  // После успешной closure invalidation закономерно убирает задачу из очереди.
  // Держим snapshot только для текущего route id, чтобы celebration не исчезал
  // между commit ответа и переходом ребёнка обратно к учебному пути.
  const taskSnapshot = useRef<{ taskId: string; task: NonNullable<typeof task> } | null>(null)
  if (task && taskId && String(task.id) === taskId) taskSnapshot.current = { taskId, task }
  const capturedTask = taskSnapshot.current
  const closureTask = task ?? (
    capturedTask?.taskId === taskId ? capturedTask?.task : undefined
  )
  const closure = useClosure(
    closureTask?.problem_id ?? 0,
    closureTask?.primary_micro_skill ?? null,
  )
  const devCelebrate = import.meta.env.DEV && new URLSearchParams(location.search).get('dev') === 'celebrate'
  const isDone = closure.status === 'correct' || devCelebrate
  const problem = closure.problem
  const isTaskNotFound = !isTaskLoading && !closureTask

  return (
    <div className="min-h-dvh bg-paper">
      <FocusTopbar meta="ПРОВЕРКА" />
      {isDone ? (
        <ClosureCelebration
          statement={problem?.statement ?? null}
          answer={closure.lastAnswer ?? null}
          topic={problem?.topic_label ?? closureTask?.topic_label ?? 'Математика'}
        />
      ) : (
        <div className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-6xl content-start gap-4 px-4 py-3 md:px-8 lg:grid-cols-[minmax(14rem,0.42fr)_minmax(0,1fr)] lg:content-center lg:items-center lg:gap-9 lg:py-8">
          <aside className="rounded-card bg-sage-soft/55 px-5 py-5 md:px-7 lg:py-8">
            <p className="text-mark text-brand-deep">Перенос навыка</p>
            <h1 className="mt-3 text-[clamp(30px,4vw,44px)] font-bold leading-[1.02] tracking-[-0.05em] text-ink">Та же мысль. Новые числа.</h1>
            <p className="mt-3 max-w-xl text-body text-text lg:mt-5">Реши без подсказок. Так проверяем ход решения, а не память ответа.</p>
            <p className="mt-3 border-t border-ink/10 pt-3 text-caption1 text-muted lg:mt-6 lg:pt-4">{problem?.topic_label ?? closureTask?.topic_label ?? 'Готовим похожую задачу'}</p>
          </aside>

          <section className="flex min-w-0 items-center" aria-label="Проверочная задача">
            <div className="w-full min-w-0">
              {isTaskNotFound ? (
                <StateBlock title="Эта задача уже недоступна" text="Вернись к учебному пути — там актуальный следующий шаг." />
              ) : closure.status === 'error' && !problem ? (
                <StateBlock
                  title="Не удалось подготовить проверку"
                  text="Связь прервалась до загрузки задачи. Попробуй ещё раз — прогресс не потерян."
                  action={<ApButton onClick={closure.retryStart}>Попробовать ещё раз</ApButton>}
                />
              ) : !problem || closure.status === 'loading' ? (
                <div role="status" aria-live="polite" className="tape-stage min-h-96 p-7">
                  <p className="text-mark text-brand-deep">Готовим контрольную</p>
                  <div className="shimmer mt-7 h-10 w-4/5 rounded-control bg-paper-2" />
                  <div className="shimmer mt-3 h-10 w-2/3 rounded-control bg-paper-2" />
                  <div className="shimmer mt-12 h-20 w-3/5 rounded-control bg-sage-soft" />
                </div>
              ) : (
                <VerificationCard
                  statement={problem.statement}
                  wrong={closure.status === 'wrong'}
                  networkError={closure.status === 'error'}
                  attempts={closure.attempts}
                  checking={closure.status === 'checking'}
                  onCheck={closure.check}
                  onResume={closure.resume}
                />
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function StateBlock({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <section className="tape-card px-6 py-8">
      <h2 className="text-h2 text-ink">{title}</h2>
      <p className="mt-4 text-study text-text">{text}</p>
      {action && <div className="mt-5">{action}</div>}
      {!action && <ApButton className="mt-6" onClick={() => window.location.assign('/app/')}>К моему пути</ApButton>}
    </section>
  )
}
