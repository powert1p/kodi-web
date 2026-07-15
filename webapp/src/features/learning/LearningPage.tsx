import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { FocusTopbar } from '../../components/FocusTopbar'
import { learningIdentity } from '../../lib/api'
import { useAuth } from '../auth/AuthContext'
import { LearningActivityView } from './LearningActivity'
import { LearningPhaseRail } from './LearningPhaseRail'
import { LearningResultView } from './LearningResult'
import { useLearningFlow } from './useLearningFlow'

export function LearningPage() {
  const { lessonId = 'mixtures-1' } = useParams()
  const { token } = useAuth()
  const flow = useLearningFlow(lessonId, learningIdentity(token))
  const focusedActivityRef = useRef<string | null>(null)

  useEffect(() => {
    const activityId = flow.state?.activity?.id ?? (flow.state?.status === 'completed' ? 'result' : null)
    if (!activityId || focusedActivityRef.current === activityId) return
    focusedActivityRef.current = activityId
    requestAnimationFrame(() => {
      const target = document.querySelector<HTMLElement>(
        flow.state?.status === 'completed' ? '#learning-result-title' : '#learning-activity-title',
      )
      target?.focus({ preventScroll: true })
    })
  }, [flow.state?.activity?.id, flow.state?.status])

  const progress = flow.state?.progress
  const meta = progress ? `Шаг ${progress.current} из ${progress.total}` : undefined

  return (
    <div className="min-h-dvh bg-paper text-text">
      <FocusTopbar label="Мой путь" meta={meta} />
      {flow.isLoading ? (
        <LearningLoading />
      ) : flow.startError && !flow.state ? (
        <LearningStartError onRetry={flow.retryStart} />
      ) : flow.state ? (
        <div className="mx-auto max-w-[90rem] px-4 pb-10 pt-2 md:px-8 lg:pb-14">
          <LessonProgress
            completed={flow.state.progress.completed}
            total={flow.state.progress.total}
            phase={flow.state.activity?.phase_label ?? 'Урок завершён'}
          />
          <div className="mt-5 grid min-w-0 gap-5 lg:grid-cols-[15rem_minmax(0,48rem)] lg:justify-center lg:gap-9">
            <LearningPhaseRail
              role={flow.state.activity?.role ?? null}
              completed={flow.state.status === 'completed'}
            />
            <div className="min-w-0">
              {flow.state.status === 'completed' && flow.state.result ? (
                <LearningResultView result={flow.state.result} />
              ) : flow.state.activity ? (
                <>
                  <div className="sr-only" aria-live="polite">
                    {flow.state.feedback?.message ?? ''}
                  </div>
                  <LearningActivityView
                    activity={flow.state.activity}
                    answer={flow.answer}
                    onAnswerChange={flow.changeAnswer}
                    onSubmit={flow.submitAnswer}
                    onAdvance={flow.advance}
                    isSubmitting={flow.isSubmitting}
                    isAdvancing={flow.isAdvancing}
                    answerError={flow.answerError}
                    advanceError={flow.advanceError}
                    feedback={flow.state.feedback}
                  />
                </>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function LessonProgress({ completed, total, phase }: { completed: number; total: number; phase: string }) {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0
  return (
    <section aria-label="Прогресс урока" className="mx-auto max-w-[65rem]">
      <div className="flex items-center justify-between gap-4 text-caption1-medium text-muted">
        <span>{phase}</span>
        <span className="font-display">{completed}/{total} сохранено</span>
      </div>
      <div
        className="mt-2 h-2 overflow-hidden rounded-chip bg-paper-2"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={completed}
      >
        <div className="h-full rounded-chip bg-brand transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${percent}%` }} />
      </div>
    </section>
  )
}

function LearningLoading() {
  return (
    <div className="mx-auto max-w-[65rem] px-4 py-4 md:px-8" role="status" aria-label="Восстанавливаем урок">
      <div className="shimmer h-2 rounded-chip bg-paper-2" />
      <div className="mt-5 grid gap-5 lg:grid-cols-[15rem_minmax(0,48rem)]">
        <div className="hidden min-h-80 rounded-control bg-paper-2 lg:block" />
        <div className="tape-stage min-h-[32rem] p-7">
          <div className="shimmer h-3 w-28 rounded-chip bg-paper-2" />
          <div className="shimmer mt-5 h-12 w-4/5 rounded-control bg-paper-2" />
          <div className="shimmer mt-8 h-24 rounded-control bg-paper-2" />
          <div className="shimmer mt-5 h-20 rounded-control bg-paper-2" />
        </div>
      </div>
    </div>
  )
}

function LearningStartError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="mx-auto flex min-h-[70dvh] max-w-2xl items-center px-5 py-10">
      <section role="alert" className="tape-stage w-full px-6 py-8 md:px-9">
        <p className="text-mark text-oxide">Связь прервалась</p>
        <h1 className="mt-3 text-h2 text-ink">Прогресс хранится на сервере</h1>
        <p className="mt-4 text-body text-muted">Повтори загрузку — урок продолжится с сохранённого шага.</p>
        <div className="mt-6"><ApButton onClick={onRetry}>Восстановить урок</ApButton></div>
      </section>
    </div>
  )
}
