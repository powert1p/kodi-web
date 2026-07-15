import type { FormEvent } from 'react'
import { ApButton } from '../../components/ApButton'
import { MathText } from '../../components/MathText'
import type { LearningActivity, LearningFeedback } from '../../lib/types'

interface LearningActivityViewProps {
  activity: LearningActivity
  answer: string
  onAnswerChange: (value: string) => void
  onSubmit: () => void
  onAdvance: () => void
  isSubmitting: boolean
  isAdvancing: boolean
  answerError: Error | null
  advanceError: Error | null
  feedback?: LearningFeedback | null
}

export function LearningActivityView({
  activity,
  answer,
  onAnswerChange,
  onSubmit,
  onAdvance,
  isSubmitting,
  isAdvancing,
  answerError,
  advanceError,
  feedback,
}: LearningActivityViewProps) {
  const isWorked = activity.role === 'worked'
  const isWrong = feedback?.is_correct === false && activity.last_answer !== null
  const networkError = answerError ?? advanceError

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <article className="tape-stage reveal min-w-0 px-5 py-6 md:px-9 md:py-9">
      <div className="border-b border-ink/10 pb-5">
        <p className="text-mark text-brand-deep">{activity.phase_label}</p>
        <h1
          id="learning-activity-title"
          tabIndex={-1}
          className="mt-3 max-w-2xl text-h2 text-ink focus-visible:outline-none"
        >
          {activity.title}
        </h1>
      </div>

      <div className="mt-6 min-w-0">
        <p className="text-study text-text">
          <MathText text={activity.statement} />
        </p>
      </div>

      {isWorked ? (
        <WorkedExample activity={activity} onAdvance={onAdvance} busy={isAdvancing} error={advanceError} />
      ) : (
        <form onSubmit={submit} className="mt-7">
          {activity.embedded_supports.length > 0 && (
            <dl className="grid gap-3 sm:grid-cols-2">
              {activity.embedded_supports.map((support, index) => (
                <div key={support} className="rounded-control bg-sage-soft px-4 py-4">
                  <dt className="text-caption1-medium text-sage-deep">Из условия {index + 1}</dt>
                  <dd className="mt-1 text-title text-ink"><MathText text={support} /></dd>
                </div>
              ))}
            </dl>
          )}

          <label htmlFor="learning-answer" className="mt-7 block text-h3 text-ink">
            {activity.prompt}
          </label>
          <div className="answer-panel mt-4 flex min-h-20 min-w-0 items-center gap-2 overflow-hidden">
            <span className="shrink-0 font-display text-title text-muted">Ответ =</span>
            <span className="bracket-slot min-w-0 flex-1" data-state={isWrong ? 'wrong' : 'active'}>
              <input
                id="learning-answer"
                name="answer"
                className="equation-input w-full max-w-none text-[clamp(26px,8vw,42px)]"
                value={answer}
                onChange={(event) => onAnswerChange(event.target.value)}
                inputMode="decimal"
                autoComplete="off"
                aria-label={`Ответ: ${activity.prompt}`}
                aria-describedby={activity.support ? 'learning-support' : undefined}
                aria-invalid={isWrong || undefined}
                placeholder="?"
                disabled={isSubmitting}
              />
            </span>
            {activity.input_suffix && (
              <span className="shrink-0 font-display text-h3 text-ink">{activity.input_suffix}</span>
            )}
          </div>

          {activity.support && (
            <aside
              id="learning-support"
              role="status"
              aria-live="polite"
              className="mt-5 rounded-control border border-sage/70 bg-sage-soft px-4 py-4 text-body text-ink"
            >
              <p className="text-mark text-sage-deep">
                {activity.support_level > 1 ? 'Опора после второй попытки' : 'Подсказка после попытки'}
              </p>
              <p className="mt-2"><MathText text={activity.support} /></p>
            </aside>
          )}

          {networkError && (
            <div role="alert" className="mt-5 rounded-control border border-oxide/25 bg-oxide-soft px-4 py-4 text-body text-oxide">
              Ответ «{answer}» остался в поле. Связь прервалась — отправь его ещё раз.
            </div>
          )}

          <div className="mt-6 flex items-center justify-between gap-4 border-t border-ink/10 pt-5">
            <p className="hidden max-w-sm text-caption1 text-muted sm:block">
              {activity.role === 'guided'
                ? 'Проверяем только этот шаг, не всю задачу сразу.'
                : 'Подсказка появится только после попытки.'}
            </p>
            <ApButton
              type="submit"
              size="l"
              full
              loading={isSubmitting}
              disabled={!answer.trim()}
              className="sm:ml-auto sm:w-auto"
            >
              {answerError
                ? 'Отправить ещё раз'
                : activity.role === 'guided'
                  ? 'Проверить шаг'
                  : 'Проверить ответ'}
            </ApButton>
          </div>
        </form>
      )}
    </article>
  )
}

function WorkedExample({
  activity,
  onAdvance,
  busy,
  error,
}: {
  activity: LearningActivity
  onAdvance: () => void
  busy: boolean
  error: Error | null
}) {
  return (
    <div className="mt-7">
      <p className="max-w-2xl text-body text-muted">{activity.prompt}</p>
      <ol className="mt-5 space-y-3">
        {activity.worked_steps.map((step, index) => (
          <li key={step.label} className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-3 rounded-control bg-sage-soft/70 px-4 py-4">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-success text-caption1-medium text-surface" aria-hidden>
              {index + 1}
            </span>
            <div className="min-w-0">
              <p className="text-caption1-medium text-sage-deep">{step.label}</p>
              <p className="mt-1 text-body text-text"><MathText text={step.expression} /></p>
              <p className="mt-1 font-display text-h3 text-success-ink"><MathText text={step.result} /></p>
            </div>
          </li>
        ))}
      </ol>
      {error && (
        <div role="alert" className="mt-5 rounded-control bg-oxide-soft px-4 py-4 text-body text-oxide">
          Не удалось сохранить переход. Разбор останется на экране — попробуй ещё раз.
        </div>
      )}
      <div className="mt-6 flex justify-end border-t border-ink/10 pt-5">
        <ApButton size="l" full loading={busy} onClick={onAdvance} className="sm:w-auto">
          Перейти к своему шагу
        </ApButton>
      </div>
    </div>
  )
}
