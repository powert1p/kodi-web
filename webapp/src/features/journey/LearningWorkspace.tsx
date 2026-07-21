import {
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from 'react'
import { BrandMark } from '../../components/BrandMark'
import { MathText } from '../../components/MathText'
import {
  CameraUploadIcon,
  CheckIcon,
  CloseIcon,
  LongArrowRightIcon,
  RestartIcon,
} from '../../icons'
import { ApiError, sendTutorMessage } from '../../lib/api'
import { hasJourneyWorkspace } from '../../lib/journeyApi'
import type {
  ActiveJourneyState,
  GuidedProcessingStep,
  GuidedStep,
  JourneyNextStep,
  JourneyTypedFeedback,
  PhotoFeedbackStep,
  PhotoRecoveryStep,
  PhotoTaskStep,
} from '../../lib/journeyApi'
import type { TutorMessage } from '../../lib/types'
import { useJourney } from './useJourney'
import './LearningWorkspace.css'

const MAX_PHOTO_BYTES = 8 * 1024 * 1024
const ACCEPTED_PHOTO_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'])

type WorkspaceStep = Extract<
  JourneyNextStep,
  {
    type:
      | 'independent_task'
      | 'transfer_task'
      | 'typed_processing'
      | 'guided_processing'
      | 'photo_processing'
      | 'guided_step'
      | 'photo_feedback'
      | 'photo_recovery'
      | 'transfer_feedback'
  }
>

type JourneyController = ReturnType<typeof useJourney>
type ResponseMode = 'photo' | 'typed'
type TutorStatus = 'idle' | 'sending' | 'error'

interface WorkspacePhoto {
  file: File
  attemptId: string
}

interface StaleTypedDraft {
  answer: string
}

interface LearningWorkspaceProps {
  journey: JourneyController
  state: ActiveJourneyState
  pendingPhoto: WorkspacePhoto | null
  onPhoto: (file: File) => void
  onClearPhoto: () => void
}

function isTaskStep(step: JourneyNextStep): step is PhotoTaskStep {
  return step.type === 'independent_task' || step.type === 'transfer_task'
}

function isGuidedStep(step: WorkspaceStep): step is GuidedStep {
  return step.type === 'guided_step'
}

function isGuidedProcessing(step: WorkspaceStep): step is GuidedProcessingStep {
  return step.type === 'guided_processing'
}

function isFeedbackStep(step: WorkspaceStep): step is PhotoFeedbackStep {
  return step.type === 'photo_feedback' || step.type === 'transfer_feedback'
}

function fileSize(size: number): string {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} КБ`
  return `${(size / (1024 * 1024)).toFixed(1)} МБ`
}

function modeLabel(state: ActiveJourneyState): string {
  if (state.next_step.type === 'guided_step' || state.next_step.type === 'guided_processing') {
    return 'Разбор по шагам'
  }
  if (state.task.mode === 'transfer') return 'Проверка переноса'
  return 'Самостоятельная работа'
}

function taskTitle(step: WorkspaceStep): string {
  if (step.type === 'typed_processing' || step.type === 'guided_processing' || step.type === 'photo_processing') {
    return 'Текущая задача'
  }
  if ('title' in step && typeof step.title === 'string') return step.title
  if (step.type === 'photo_recovery') return 'Продолжаем эту задачу'
  if (isFeedbackStep(step)) return step.verdict === 'correct' ? 'Решение проверено' : 'Продолжаем эту задачу'
  return 'Текущая задача'
}

function stageLabel(step: WorkspaceStep): string {
  if (step.type === 'typed_processing') return 'Проверяем ответ'
  if (step.type === 'guided_processing') return `Проверяем шаг ${step.step.number}`
  if (step.type === 'photo_processing') return 'Проверяем фото'
  if (step.type === 'guided_step') return `Шаг ${step.step.number} из ${step.step.total}`
  if (step.type === 'photo_recovery') return 'Попытка сохранена'
  if (isFeedbackStep(step)) return step.verdict === 'correct' ? 'Готово' : 'Нужна одна правка'
  return 'Можно отвечать'
}

function recoveryTitle(reason: PhotoRecoveryStep['reason']): string {
  if (reason === 'provider_error') return 'Проверка временно на паузе'
  if (reason === 'wrong_photo') return 'На фото не видно решения этой задачи'
  if (reason === 'unreadable') return 'Запись не удалось прочитать'
  return 'Нужен более ясный снимок'
}

function focusLabel(feedback: JourneyTypedFeedback): string {
  if (feedback.verdict === 'correct') return 'Ответ принят'
  if (feedback.verdict === 'unsure') return 'Проверим другим способом'
  if (feedback.error_focus === 'interpretation') return 'Перечитай, что требуется найти'
  if (feedback.error_focus === 'calculation') return 'Проверь вычисления'
  if (feedback.error_focus === 'units') return 'Проверь единицы'
  if (feedback.error_focus === 'format') return 'Проверь формат ответа'
  return 'Попробуй ещё раз'
}

function feedbackAction(step: PhotoFeedbackStep): string {
  if (step.verdict !== 'correct') return 'retry_task'
  if (step.type === 'photo_feedback') return 'start_transfer'
  return step.mastery?.reached === false ? 'continue_transfer' : 'finish_topic'
}

function currentGuidedStep(step: WorkspaceStep): GuidedStep['step'] | null {
  return isGuidedStep(step) || isGuidedProcessing(step) ? step.step : null
}

export function LearningWorkspace({
  journey,
  state,
  pendingPhoto,
  onPhoto,
  onClearPhoto,
}: LearningWorkspaceProps) {
  const step = state.next_step as WorkspaceStep
  const taskKey = `${state.journey_id}:${state.task.problem_id}`
  const guidedStep = currentGuidedStep(step)
  const guidedKey = guidedStep ? `${taskKey}:${guidedStep.number}` : null
  const photoInputId = useId()
  const typedInputId = useId()
  const guidedInputId = useId()
  const tutorId = useId()
  const tutorTitleId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const tutorTriggerRef = useRef<HTMLButtonElement>(null)
  const tutorInputRef = useRef<HTMLTextAreaElement>(null)
  const tutorSheetRef = useRef<HTMLElement>(null)
  const tutorHistoryRef = useRef<HTMLDivElement>(null)
  const taskAnchorRef = useRef<HTMLElement>(null)
  const taskHeadingRef = useRef<HTMLHeadingElement>(null)
  const typedFormRef = useRef<HTMLFormElement>(null)
  const typedInputRef = useRef<HTMLInputElement>(null)
  const guidedInputRef = useRef<HTMLInputElement>(null)
  const typedFeedbackRef = useRef<HTMLDivElement>(null)
  const typedDraftsRef = useRef(new Map<string, string>())
  const guidedDraftsRef = useRef(new Map<string, string>())
  const typedAdvanceTaskRef = useRef<string | null>(null)
  const typedFocusRequestedRef = useRef(false)
  const [responseMode, setResponseMode] = useState<ResponseMode>(state.response.default_mode)
  const [typedDraft, setTypedDraft] = useState('')
  const [typedError, setTypedError] = useState<string | null>(null)
  const [typedSuccess, setTypedSuccess] = useState<string | null>(null)
  const [typedFeedbackFocus, setTypedFeedbackFocus] = useState<{
    taskKey: string
    revision: number
  } | null>(null)
  const [staleTypedDraft, setStaleTypedDraft] = useState<StaleTypedDraft | null>(null)
  const [guidedDraft, setGuidedDraft] = useState('')
  const [guidedError, setGuidedError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [parentHandoff, setParentHandoff] = useState(false)
  const [adultConfirmed, setAdultConfirmed] = useState(false)
  const [tutorOpen, setTutorOpen] = useState(false)
  const [tutorDraft, setTutorDraft] = useState('')
  const [tutorHistory, setTutorHistory] = useState<TutorMessage[]>([])
  const [tutorStatus, setTutorStatus] = useState<TutorStatus>('idle')
  const [tutorError, setTutorError] = useState<string | null>(null)

  const preservedTypedAnswer = step.type === 'typed_processing'
    ? step.preserved_answer.value
    : isTaskStep(step)
      ? step.preserved_answer?.value ?? null
      : null

  useEffect(() => {
    typedFocusRequestedRef.current = false
    setTypedFeedbackFocus(null)
    setResponseMode(state.response.default_mode)
    setTypedDraft(typedDraftsRef.current.get(taskKey) ?? '')
    setTypedError(null)
    if (typedAdvanceTaskRef.current !== taskKey) setTypedSuccess(null)
    setFileError(null)
    setParentHandoff(false)
    setAdultConfirmed(false)
    setTutorOpen(false)
    setTutorDraft('')
    setTutorHistory([])
    setTutorStatus('idle')
    setTutorError(null)
  }, [state.response.default_mode, taskKey])

  useEffect(() => {
    if (!preservedTypedAnswer) return
    typedDraftsRef.current.set(taskKey, preservedTypedAnswer)
    setTypedDraft(preservedTypedAnswer)
    setTypedError(null)
    setResponseMode('typed')
  }, [preservedTypedAnswer, taskKey])

  useEffect(() => {
    if (!guidedKey) {
      setGuidedDraft('')
      setGuidedError(null)
      return
    }
    const serverAnswer = isGuidedProcessing(step)
      ? step.preserved_answer.value
      : isGuidedStep(step)
        ? step.feedback?.answer ?? null
        : null
    const answer = serverAnswer ?? guidedDraftsRef.current.get(guidedKey) ?? ''
    if (answer) guidedDraftsRef.current.set(guidedKey, answer)
    setGuidedDraft(answer)
    setGuidedError(null)
  }, [guidedKey, state.revision, step])

  useEffect(() => {
    setTutorOpen(false)
    setTutorDraft('')
    setTutorHistory([])
    setTutorStatus('idle')
    setTutorError(null)
  }, [guidedKey])

  const typedFeedback = isTaskStep(step) ? step.typed_feedback ?? null : null

  useEffect(() => {
    if (
      !typedFeedback
      || !typedFeedbackFocus
      || typedFeedbackFocus.taskKey !== taskKey
      || typedFeedbackFocus.revision !== state.revision
    ) return

    let secondFrame: number | null = null
    let focusFrame: number | null = null
    const firstFrame = requestAnimationFrame(() => {
      secondFrame = requestAnimationFrame(() => {
        focusFrame = requestAnimationFrame(() => {
          typedFeedbackRef.current?.focus({ preventScroll: true })
          setTypedFeedbackFocus(null)
        })
      })
    })
    return () => {
      cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) cancelAnimationFrame(secondFrame)
      if (focusFrame !== null) cancelAnimationFrame(focusFrame)
    }
  }, [state.revision, taskKey, typedFeedback, typedFeedbackFocus])

  useEffect(() => {
    if (typedAdvanceTaskRef.current !== taskKey) return
    typedAdvanceTaskRef.current = null
    requestAnimationFrame(() => {
      taskHeadingRef.current?.focus({ preventScroll: true })
      taskAnchorRef.current?.scrollIntoView?.({ block: 'start', behavior: 'smooth' })
    })
  }, [taskKey])

  useEffect(() => {
    if (responseMode !== 'typed' || !typedFocusRequestedRef.current) return
    typedFocusRequestedRef.current = false
    let focusFrame: number | null = null
    const firstFrame = requestAnimationFrame(() => {
      focusFrame = requestAnimationFrame(() => {
        if (window.matchMedia?.('(orientation: landscape) and (max-height: 34rem)').matches) {
          typedFormRef.current?.scrollIntoView?.({ block: 'end' })
        }
        typedInputRef.current?.focus({ preventScroll: true })
      })
    })
    return () => {
      cancelAnimationFrame(firstFrame)
      if (focusFrame !== null) cancelAnimationFrame(focusFrame)
    }
  }, [responseMode])

  const consentRequired = isTaskStep(step)
    && (step.photo_consent_required || journey.issue?.code === 'consent_required')

  useEffect(() => {
    if (!consentRequired) {
      setParentHandoff(false)
      setAdultConfirmed(false)
    }
  }, [consentRequired])

  const canTutor = !(
    step.type === 'photo_processing'
    || step.type === 'typed_processing'
    || step.type === 'guided_processing'
  )

  useEffect(() => {
    if (!canTutor && tutorOpen) setTutorOpen(false)
  }, [canTutor, tutorOpen])

  useEffect(() => {
    if (!tutorOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const frame = requestAnimationFrame(() => tutorInputRef.current?.focus({ preventScroll: true }))
    return () => {
      cancelAnimationFrame(frame)
      document.body.style.overflow = previousOverflow
    }
  }, [tutorOpen])

  useEffect(() => {
    if (!tutorOpen) return
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      setTutorOpen(false)
      requestAnimationFrame(() => tutorTriggerRef.current?.focus({ preventScroll: true }))
    }
    document.addEventListener('keydown', handleEscape, true)
    return () => document.removeEventListener('keydown', handleEscape, true)
  }, [tutorOpen])

  useEffect(() => {
    if (!tutorOpen) return
    tutorHistoryRef.current?.scrollTo?.({ top: tutorHistoryRef.current.scrollHeight })
  }, [tutorHistory, tutorOpen, tutorStatus])

  function openTutor() {
    if (!canTutor) return
    setTutorOpen(true)
    setTutorError(null)
  }

  function closeTutor() {
    setTutorOpen(false)
    requestAnimationFrame(() => tutorTriggerRef.current?.focus({ preventScroll: true }))
  }

  function trapTutorFocus(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeTutor()
      return
    }
    if (event.key !== 'Tab') return
    const focusable = Array.from(
      tutorSheetRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    )
    if (focusable.length === 0) return
    const first = focusable[0]!
    const last = focusable[focusable.length - 1]!
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function selectPhoto(file: File | undefined) {
    if (!file) return
    const extensionAllowed = /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name)
    if ((!ACCEPTED_PHOTO_TYPES.has(file.type) && !extensionAllowed) || file.size === 0) {
      setFileError('Выбери фото в формате JPEG, PNG, WEBP или HEIC.')
      return
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setFileError('Фото больше 8 МБ. Уменьши его или сделай новый снимок.')
      return
    }
    setFileError(null)
    onPhoto(file)
  }

  function selectResponseMode(mode: ResponseMode) {
    typedFocusRequestedRef.current = mode === 'typed'
    setResponseMode(mode)
    setFileError(null)
  }

  async function submitTyped(event: FormEvent) {
    event.preventDefault()
    const answer = typedDraft.trim()
    if (!answer) {
      setTypedError('Введи свой ответ')
      return
    }
    if (answer.length > 500) {
      setTypedError('Сократи ответ до 500 символов')
      return
    }
    setTypedError(null)
    setTypedSuccess(null)
    const result = await journey.answerTyped(
      state.task.problem_id,
      answer,
      (authoritativeState, issue) => {
        if (!hasJourneyWorkspace(authoritativeState)) return
        const authoritativeTaskKey = `${authoritativeState.journey_id}:${authoritativeState.task.problem_id}`
        if (authoritativeTaskKey !== taskKey) {
          if (issue.status === 409) setStaleTypedDraft({ answer })
          return
        }
        if (isTaskStep(authoritativeState.next_step) && authoritativeState.next_step.typed_feedback) {
          setTypedFeedbackFocus({ taskKey, revision: authoritativeState.revision })
        }
      },
    )
    if (!result) return
    const nextTaskKey = hasJourneyWorkspace(result)
      ? `${result.journey_id}:${result.task.problem_id}`
      : null
    if (nextTaskKey && nextTaskKey !== taskKey) {
      typedDraftsRef.current.delete(taskKey)
      typedAdvanceTaskRef.current = nextTaskKey
      setTypedSuccess('Ответ принят. Открываем новую задачу.')
    } else if (
      hasJourneyWorkspace(result)
      && isTaskStep(result.next_step)
      && result.next_step.typed_feedback
    ) {
      setTypedFeedbackFocus({ taskKey, revision: result.revision })
    } else if (result.next_step.type === 'topic_result') {
      typedDraftsRef.current.delete(taskKey)
      setTypedSuccess('Ответ принят. Навык подтверждён.')
    }
  }

  function updateTypedDraft(value: string) {
    setTypedDraft(value)
    if (value) typedDraftsRef.current.set(taskKey, value)
    else typedDraftsRef.current.delete(taskKey)
    setTypedError(null)
  }

  function restoreStaleTypedDraft() {
    if (!staleTypedDraft) return
    updateTypedDraft(staleTypedDraft.answer)
    setStaleTypedDraft(null)
    selectResponseMode('typed')
  }

  function updateGuidedDraft(value: string) {
    setGuidedDraft(value)
    setGuidedError(null)
    if (!guidedKey) return
    if (value) guidedDraftsRef.current.set(guidedKey, value)
    else guidedDraftsRef.current.delete(guidedKey)
  }

  async function submitGuided(event: FormEvent) {
    event.preventDefault()
    if (!isGuidedStep(step) || !guidedKey) return
    const answer = guidedDraft.trim()
    if (!answer) {
      setGuidedError('Введи ответ этого шага')
      return
    }
    setGuidedError(null)
    guidedDraftsRef.current.set(guidedKey, answer)
    const result = await journey.answerGuided(step.problem.id, step.step.number, answer)
    if (!result) return
    const next = result.next_step
    if (next.type !== 'guided_processing' && (
      next.type !== 'guided_step'
      || next.problem.id !== step.problem.id
      || next.step.number !== step.step.number
    )) {
      guidedDraftsRef.current.delete(guidedKey)
    }
  }

  async function submitTutor(event: FormEvent) {
    event.preventDefault()
    const message = tutorDraft.trim()
    if (!message || tutorStatus === 'sending') return
    setTutorStatus('sending')
    setTutorError(null)
    const decompIdx = step.problem.content_idx
    const stepN = isGuidedStep(step) || isGuidedProcessing(step)
      ? step.step.number
      : step.type === 'photo_feedback'
        ? step.failed_step ?? null
        : null
    try {
      const result = await sendTutorMessage(state.task.problem_id, message, decompIdx, stepN)
      setTutorHistory(result.history)
      setTutorDraft('')
      setTutorStatus('idle')
    } catch (error) {
      setTutorError(
        error instanceof ApiError && error.status === 429
          ? 'Слишком много сообщений подряд. Подожди минуту и продолжим.'
          : 'Помощник временно не ответил. Вопрос остался в поле — попробуй ещё раз.',
      )
      setTutorStatus('error')
    }
  }

  function uploadPhoto() {
    if (!pendingPhoto || !isTaskStep(step)) return
    void journey.uploadPhoto(step.problem.id, pendingPhoto.file, state.revision, pendingPhoto.attemptId)
  }

  function continueFeedback(feedback: PhotoFeedbackStep) {
    void journey.continueWith(feedbackAction(feedback))
  }

  function retryRecovery(recovery: PhotoRecoveryStep) {
    if (recovery.reason === 'provider_error') {
      void journey.retryPhoto()
      return
    }
    onClearPhoto()
    void journey.continueWith('retry_photo')
  }

  const busy = journey.pendingAction !== null
  const issue = journey.issue?.code === 'consent_required' ? null : journey.issue?.message ?? null
  const tone = typedFeedback?.verdict === 'correct' || (isFeedbackStep(step) && step.verdict === 'correct')
    ? 'correct'
    : typedFeedback?.verdict === 'incorrect' || (isFeedbackStep(step) && step.verdict === 'incorrect')
      ? 'revision'
      : step.type === 'photo_recovery'
        ? 'uncertain'
        : step.type.endsWith('_processing')
          ? 'processing'
          : isGuidedStep(step)
            ? 'guided'
            : 'ready'

  return (
    <section
      className={`learning-workspace learning-workspace--${tone}`}
      data-testid="learning-workspace"
      data-stage={step.type}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && tutorOpen) {
          event.preventDefault()
          closeTutor()
        }
      }}
    >
      <header className="workbook-session" aria-label="Текущая учебная сессия">
        <BrandMark className="workbook-session__brand" />
        <div className="workbook-session__topic">
          <span>{state.task.topic.title}</span>
          <strong>{modeLabel(state)}</strong>
        </div>
        <div className="workbook-session__progress">
          <span aria-hidden />
          Задача {state.task.position}
        </div>
      </header>

      <main className="workbook-layout">
        <article
          ref={taskAnchorRef}
          className="workbook-task"
          aria-labelledby="learning-task-title"
          data-testid="task-anchor"
        >
          <div className="workbook-task__meta">
            <span>Задача {state.task.position}</span>
            <span>{stageLabel(step)}</span>
          </div>
          <h1 id="learning-task-title" ref={taskHeadingRef} tabIndex={-1}>{taskTitle(step)}</h1>
          <div className="workbook-task__statement" data-testid="workbook-task-statement">
            <MathText text={state.task.statement} />
          </div>
          <EvidenceStrip state={state} step={step} pendingPhoto={pendingPhoto} />
        </article>

        <section
          className="workbook-composer"
          aria-labelledby="workbook-stage-title"
          data-testid="response-dock"
        >
          <StageContent
            state={state}
            step={step}
            responseMode={responseMode}
            typedFeedback={typedFeedback}
            typedFeedbackRef={typedFeedbackRef}
            pendingPhoto={pendingPhoto}
            consentRequired={consentRequired}
            parentHandoff={parentHandoff}
            adultConfirmed={adultConfirmed}
            fileError={fileError}
            issue={issue}
            onAdultConfirmed={setAdultConfirmed}
          />

          {staleTypedDraft && (
            <div className="workbook-draft-recovery" role="status" aria-live="polite" aria-atomic="true">
              <p><b>Открыта другая задача.</b> Предыдущий ответ сохранён отдельно.</p>
              <div className="workbook-inline-actions">
                <button type="button" onClick={restoreStaleTypedDraft}>Восстановить ответ в поле</button>
                <button type="button" onClick={() => setStaleTypedDraft(null)}>Скрыть</button>
              </div>
            </div>
          )}

          {!tutorOpen ? (
            <ActionComposer
              journey={journey}
              state={state}
              step={step}
              busy={busy}
              responseMode={responseMode}
              typedFeedback={typedFeedback}
              typedInputId={typedInputId}
              typedDraft={typedDraft}
              typedError={typedError}
              guidedInputId={guidedInputId}
              guidedDraft={guidedDraft}
              guidedError={guidedError}
              pendingPhoto={pendingPhoto}
              consentRequired={consentRequired}
              parentHandoff={parentHandoff}
              adultConfirmed={adultConfirmed}
              canTutor={canTutor}
              tutorTriggerRef={tutorTriggerRef}
              tutorId={tutorId}
              typedFormRef={typedFormRef}
              typedInputRef={typedInputRef}
              guidedInputRef={guidedInputRef}
              onResponseMode={selectResponseMode}
              onTypedDraft={updateTypedDraft}
              onGuidedDraft={updateGuidedDraft}
              onSubmitTyped={submitTyped}
              onSubmitGuided={submitGuided}
              onOpenPhoto={() => fileInputRef.current?.click()}
              onUploadPhoto={uploadPhoto}
              onClearPhoto={onClearPhoto}
              onParentHandoff={setParentHandoff}
              onGrantConsent={() => void journey.grantPhotoConsent()}
              onOpenTutor={openTutor}
              onContinueFeedback={continueFeedback}
              onRetryRecovery={retryRecovery}
            />
          ) : null}

          {isTaskStep(step) && !tutorOpen && (
            <input
              ref={fileInputRef}
              id={photoInputId}
              className="sr-only"
              tabIndex={-1}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif"
              capture="environment"
              aria-label="Фото всего решения"
              disabled={busy}
              onChange={(event) => {
                selectPhoto(event.target.files?.[0])
                event.currentTarget.value = ''
              }}
            />
          )}
        </section>
      </main>

      {tutorOpen && (
        <TutorSheet
          id={tutorId}
          titleId={tutorTitleId}
          sheetRef={tutorSheetRef}
          inputRef={tutorInputRef}
          historyRef={tutorHistoryRef}
          statement={state.task.statement}
          draft={tutorDraft}
          history={tutorHistory}
          status={tutorStatus}
          error={tutorError}
          onDraft={setTutorDraft}
          onSubmit={submitTutor}
          onClose={closeTutor}
          onKeyDown={trapTutorFocus}
        />
      )}

      <div className="workspace-live-region" data-testid="workspace-live-region" aria-live="polite" aria-atomic="true">
        {typedSuccess ?? (journey.pendingAction === 'typed-answer' && 'Проверяем короткий ответ')}
        {journey.pendingAction === 'guided-answer' && 'Проверяем ответ шага'}
        {journey.pendingAction === 'photo' && 'Фото отправляется на проверку'}
        {tutorStatus === 'sending' && 'Помощник отвечает на вопрос'}
      </div>
    </section>
  )
}

function EvidenceStrip({
  state,
  step,
  pendingPhoto,
}: {
  state: ActiveJourneyState
  step: WorkspaceStep
  pendingPhoto: WorkspacePhoto | null
}) {
  let content
  if (pendingPhoto && isTaskStep(step)) {
    content = (
      <><CheckIcon /><span><b>{pendingPhoto.file.name}</b>{fileSize(pendingPhoto.file.size)} · готово к отправке</span></>
    )
  } else if (step.type === 'typed_processing') {
    content = <><span className="workbook-pulse" aria-hidden /><span><b>{step.preserved_answer.value}</b> · ответ проверяется</span></>
  } else if (step.type === 'guided_processing') {
    content = <><span className="workbook-pulse" aria-hidden /><span><b>{step.preserved_answer.value}</b> · шаг проверяется</span></>
  } else if (step.type === 'photo_processing') {
    content = <><span className="workbook-pulse" aria-hidden /><span><b>{step.preserved_photo.name}</b> · фото проверяется</span></>
  } else if (step.type === 'guided_step') {
    content = <><span className="workbook-line" aria-hidden /><span>Сейчас нужен только ответ текущего шага — без фото</span></>
  } else if (step.type === 'photo_recovery') {
    content = <><CheckIcon /><span><b>{step.preserved_photo.name}</b> · попытка сохранена</span></>
  } else if (isFeedbackStep(step)) {
    content = <><CheckIcon /><span>{state.learner_evidence.label ?? 'Полное решение проверено'}</span></>
  } else if (isTaskStep(step) && step.typed_feedback) {
    content = <><CheckIcon /><span><b>{step.preserved_answer?.value ?? state.learner_evidence.label ?? 'Ответ'}</b> · ответ проверен</span></>
  } else {
    content = <><span className="workbook-line" aria-hidden /><span>Можно ввести итоговый ответ или отправить фото всей страницы</span></>
  }

  return (
    <div className="workbook-task__summary" data-testid="workbook-task-summary" aria-label="Текущая работа ученика">
      {content}
    </div>
  )
}

interface StageContentProps {
  state: ActiveJourneyState
  step: WorkspaceStep
  responseMode: ResponseMode
  typedFeedback: JourneyTypedFeedback | null
  typedFeedbackRef: RefObject<HTMLDivElement | null>
  pendingPhoto: WorkspacePhoto | null
  consentRequired: boolean
  parentHandoff: boolean
  adultConfirmed: boolean
  fileError: string | null
  issue: string | null
  onAdultConfirmed: (value: boolean) => void
}

function StageContent(props: StageContentProps) {
  const { step } = props
  let content

  if (props.typedFeedback) {
    content = (
      <div
        ref={props.typedFeedbackRef}
        className={`workbook-feedback workbook-feedback--${props.typedFeedback.verdict}`}
        data-testid="workbook-feedback"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        tabIndex={-1}
      >
        <StageHeading kicker="Проверка ответа" title={focusLabel(props.typedFeedback)} />
        <p>{props.typedFeedback.message}</p>
        <small> Исправь ответ или отправь фото. Можно также попросить помощь.</small>
      </div>
    )
  } else if (isTaskStep(step) && props.responseMode === 'typed') {
    content = (
      <>
        <StageHeading kicker="Ответ без фото" title="Введи свой итоговый ответ" />
        <p>AI проверит смысл и допустимую форму ответа. Если всё верно, сразу откроется следующая задача — фото не понадобится.</p>
      </>
    )
  } else if (isTaskStep(step) && props.consentRequired) {
    content = props.parentHandoff ? (
      <>
        <StageHeading kicker="Для взрослого" title="Разрешение на проверку фото" />
        <p>AiPlus использует снимок только для проверки решения и обратной связи ребёнку.</p>
        <label className="workbook-consent">
          <input
            type="checkbox"
            checked={props.adultConfirmed}
            onChange={(event) => props.onAdultConfirmed(event.target.checked)}
          />
          <span>Я родитель или законный представитель и разрешаю использовать фото решения для проверки.</span>
        </label>
      </>
    ) : (
      <>
        <StageHeading kicker="Один раз перед фото" title="Позови взрослого на короткий шаг" />
        <p>Взрослый разрешит проверку фото. После этого ты сразу вернёшься к задаче.</p>
      </>
    )
  } else if (step.type === 'typed_processing') {
    content = (
      <>
        <StageHeading kicker="Ответ сохранён" title="Проверяем ответ" />
        <p>{step.message}</p>
        <SavedEvidence value={step.preserved_answer.value} note="ответ уже на сервере" />
      </>
    )
  } else if (step.type === 'guided_processing') {
    content = (
      <>
        <StageHeading kicker={`Шаг ${step.step.number} из ${step.step.total}`} title="Проверяем этот переход" />
        <p>{step.message}</p>
        <SavedEvidence value={step.preserved_answer.value} note="ответ шага сохранён" />
      </>
    )
  } else if (step.type === 'photo_processing') {
    content = (
      <>
        <StageHeading kicker="Фото сохранено" title="AI смотрит весь ход решения" />
        <p>{step.message}</p>
        <SavedEvidence value={step.preserved_photo.name} note="переснимать не нужно" />
      </>
    )
  } else if (step.type === 'guided_step') {
    const prompt = step.step.prompt || 'Ответь только на этот шаг'
    const formatHint = step.step.format_hint || 'Введи короткий ответ текущего шага.'
    const example = step.step.example || ''
    content = (
      <div className="guided-contract" data-testid="guided-contract">
        <StageHeading kicker={`Шаг ${step.step.number} из ${step.step.total}`} title={prompt} />
        <div className="guided-contract__instruction"><MathText text={step.step.instruction} /></div>
        <div className="guided-contract__format" data-testid="guided-format-hint">
          <span>Что написать</span>
          <p>{formatHint}</p>
          {example && <small data-testid="guided-example">Например: {example}</small>}
        </div>
        {step.feedback && (
          <div className={`workbook-feedback workbook-feedback--${step.feedback.verdict}`} role="status">
            <b>{step.feedback.verdict === 'correct' ? 'Шаг принят' : 'Пока не сходится'}</b>
            <span>{step.feedback.message}</span>
          </div>
        )}
        <p className="workbook-mastery-note">Разбор помогает понять способ. Уровень подтвердит следующая самостоятельная задача.</p>
      </div>
    )
  } else if (isFeedbackStep(step)) {
    content = step.verdict === 'correct' ? (
      <>
        <StageHeading kicker="Решение проверено" title="Ход решения сошёлся" />
        <p>{step.message}</p>
        {step.mastery && <MasterySummary mastery={step.mastery} />}
      </>
    ) : (
      <>
        <StageHeading kicker={`Первое расхождение · шаг ${step.failed_step ?? '—'}`} title="Исправь одно место" />
        <p>{step.message}</p>
        {step.confirmed_steps && step.confirmed_steps.length > 0 && (
          <div className="workbook-confirmed">
            <b><CheckIcon />До этого места верно</b>
            {step.confirmed_steps.map((item) => <span key={item.number}>{item.label}</span>)}
          </div>
        )}
        {step.correction && (
          <p className="workbook-correction"><b>Что проверить:</b> действие, вычисление и единицы в этом переходе. Ответ пока не раскрываем.</p>
        )}
      </>
    )
  } else if (step.type === 'photo_recovery') {
    content = (
      <div className="workbook-recovery" role={step.reason === 'provider_error' ? 'alert' : 'status'}>
        <StageHeading kicker="Попытка не потеряна" title={recoveryTitle(step.reason)} />
        <p>{step.message}</p>
        <SavedEvidence value={step.preserved_photo.name} note="предыдущая попытка сохранена" />
        <small>{step.reason === 'provider_error' ? 'Переснимать не нужно: повторим проверку того же файла.' : 'Замени снимок без штрафа за решение.'}</small>
      </div>
    )
  } else if (props.pendingPhoto) {
    content = (
      <>
        <StageHeading kicker="Фото готово" title="Проверь снимок перед отправкой" />
        <p>Должны быть видны условие, вычисления и итоговый ответ.</p>
      </>
    )
  } else {
    content = (
      <>
        <StageHeading kicker="Твоя работа" title="Сначала реши задачу целиком" />
        <p>Введи итоговый ответ или сфотографируй страницу — AI проверит выбранный формат.</p>
      </>
    )
  }

  return (
    <div className="workbook-stage" data-testid="contextual-layer">
      {content}
      {(props.fileError || props.issue) && (
        <div className="workbook-inline-error" role="alert">{props.fileError ?? props.issue}</div>
      )}
    </div>
  )
}

function StageHeading({ kicker, title }: { kicker: string; title: string }) {
  return (
    <div className="workbook-stage__heading">
      <span>{kicker}</span>
      <h2 id="workbook-stage-title">{title}</h2>
    </div>
  )
}

function SavedEvidence({ value, note }: { value: string; note: string }) {
  return (
    <div className="workbook-saved"><CheckIcon /><span><b>{value}</b>{note}</span></div>
  )
}

interface ActionComposerProps {
  journey: JourneyController
  state: ActiveJourneyState
  step: WorkspaceStep
  busy: boolean
  responseMode: ResponseMode
  typedFeedback: JourneyTypedFeedback | null
  typedInputId: string
  typedDraft: string
  typedError: string | null
  guidedInputId: string
  guidedDraft: string
  guidedError: string | null
  pendingPhoto: WorkspacePhoto | null
  consentRequired: boolean
  parentHandoff: boolean
  adultConfirmed: boolean
  canTutor: boolean
  tutorTriggerRef: RefObject<HTMLButtonElement | null>
  tutorId: string
  typedFormRef: RefObject<HTMLFormElement | null>
  typedInputRef: RefObject<HTMLInputElement | null>
  guidedInputRef: RefObject<HTMLInputElement | null>
  onResponseMode: (mode: ResponseMode) => void
  onTypedDraft: (value: string) => void
  onGuidedDraft: (value: string) => void
  onSubmitTyped: (event: FormEvent) => void
  onSubmitGuided: (event: FormEvent) => void
  onOpenPhoto: () => void
  onUploadPhoto: () => void
  onClearPhoto: () => void
  onParentHandoff: (value: boolean) => void
  onGrantConsent: () => void
  onOpenTutor: () => void
  onContinueFeedback: (step: PhotoFeedbackStep) => void
  onRetryRecovery: (step: PhotoRecoveryStep) => void
}

function ActionComposer(props: ActionComposerProps) {
  const { step, busy } = props

  if (isTaskStep(step)) {
    return (
      <div className="workbook-action-area" data-testid="workbook-composer">
        {props.state.response.typed_available && (
          <div className="workbook-mode-switch" role="group" aria-label="Как отправить решение">
            <button
              type="button"
              aria-pressed={props.responseMode === 'typed'}
              disabled={busy}
              onClick={() => props.onResponseMode('typed')}
            >
              Ввести ответ
            </button>
            <button
              type="button"
              aria-pressed={props.responseMode === 'photo'}
              disabled={busy}
              onClick={() => props.onResponseMode('photo')}
            >
              Отправить фото
            </button>
          </div>
        )}

        {props.responseMode === 'typed' ? (
          <form ref={props.typedFormRef} className="workbook-answer-form" onSubmit={props.onSubmitTyped}>
            <label htmlFor={props.typedInputId}>Короткий ответ</label>
            <input
              ref={props.typedInputRef}
              id={props.typedInputId}
              data-testid="workbook-answer-input"
              value={props.typedDraft}
              placeholder="Напиши итоговый ответ"
              maxLength={500}
              inputMode="text"
              autoComplete="off"
              disabled={busy}
              aria-describedby={props.typedError ? `${props.typedInputId}-error` : undefined}
              onChange={(event) => props.onTypedDraft(event.target.value)}
            />
            {props.typedError && <p id={`${props.typedInputId}-error`} className="workbook-field-error" role="alert">{props.typedError}</p>}
            <PrimaryButton type="submit" disabled={busy}>
              {busy ? 'Проверяем…' : retryLabel(props.journey.issue?.code) ? 'Повторить проверку' : 'Проверить ответ'}
            </PrimaryButton>
            <SecondaryActions props={props} helpLabel="Не знаю, как начать" />
          </form>
        ) : (
          <PhotoActions props={props} />
        )}
      </div>
    )
  }

  if (step.type === 'typed_processing' || step.type === 'photo_processing') {
    const typed = step.type === 'typed_processing'
    return (
      <div className="workbook-action-area workbook-action-area--processing">
        <PrimaryButton disabled>{typed ? 'AI проверяет ответ…' : 'AI проверяет решение…'}</PrimaryButton>
        <button className="workbook-text-action" type="button" disabled={props.journey.isFetching} onClick={() => void props.journey.refresh()}>
          <RestartIcon />Проверить статус
        </button>
      </div>
    )
  }

  if (step.type === 'guided_processing') {
    return (
      <div className="workbook-action-area workbook-action-area--processing" data-testid="guided-processing">
        <label htmlFor={props.guidedInputId}>Твой ответ шага</label>
        <input id={props.guidedInputId} value={step.preserved_answer.value} disabled readOnly />
        <PrimaryButton disabled>AI проверяет шаг…</PrimaryButton>
        <button className="workbook-text-action" type="button" disabled={props.journey.isFetching} onClick={() => void props.journey.refresh()}>
          <RestartIcon />Проверить статус
        </button>
      </div>
    )
  }

  if (step.type === 'guided_step') {
    return (
      <form className="workbook-action-area workbook-answer-form" onSubmit={props.onSubmitGuided}>
        <label htmlFor={props.guidedInputId}>Ответ шага</label>
        <input
          ref={props.guidedInputRef}
          id={props.guidedInputId}
          data-testid="workbook-answer-input"
          aria-label="Ответ шага"
          value={props.guidedDraft}
          placeholder={step.step.example ? `Например: ${step.step.example}` : 'Введи короткий ответ'}
          maxLength={500}
          inputMode={step.step.input_mode || 'text'}
          autoComplete="off"
          disabled={busy}
          aria-describedby={props.guidedError ? `${props.guidedInputId}-error` : undefined}
          onChange={(event) => props.onGuidedDraft(event.target.value)}
        />
        {props.guidedError && <p id={`${props.guidedInputId}-error`} className="workbook-field-error" role="alert">{props.guidedError}</p>}
        <PrimaryButton type="submit" disabled={busy}>{busy ? 'Проверяем…' : step.primary_action}</PrimaryButton>
        <SecondaryActions props={props} />
      </form>
    )
  }

  if (isFeedbackStep(step)) {
    return (
      <div className="workbook-action-area">
        <PrimaryButton disabled={busy} onClick={() => props.onContinueFeedback(step)}>{step.primary_action}</PrimaryButton>
        <div className="workspace-secondary-actions" data-testid="workspace-secondary-actions">
          {step.verdict === 'incorrect' && step.help_available && (
            <button type="button" disabled={busy} onClick={() => void props.journey.continueWith('review_with_help')}>Разобрать по шагам</button>
          )}
          {props.canTutor && <TutorTrigger props={props} />}
        </div>
      </div>
    )
  }

  return (
    <div className="workbook-action-area">
      <PrimaryButton disabled={busy} onClick={() => props.onRetryRecovery(step)}>
        {step.reason === 'provider_error' ? 'Повторить проверку' : step.primary_action}
      </PrimaryButton>
    </div>
  )
}

function PhotoActions({ props }: { props: ActionComposerProps }) {
  const { step, busy } = props
  if (!isTaskStep(step)) return null
  const primaryLabel = props.consentRequired
    ? props.parentHandoff ? 'Разрешить проверку фото' : 'Позвать взрослого'
    : props.pendingPhoto ? 'Отправить решение' : step.primary_action
  const primaryAction = props.consentRequired
    ? props.parentHandoff ? props.onGrantConsent : () => props.onParentHandoff(true)
    : props.pendingPhoto ? props.onUploadPhoto : props.onOpenPhoto

  return (
    <div className="workbook-photo-actions">
      {props.pendingPhoto && !props.consentRequired && (
        <div className="workbook-photo-file">
          <CheckIcon />
          <span><b>{props.pendingPhoto.file.name}</b>{fileSize(props.pendingPhoto.file.size)}</span>
          <button type="button" disabled={busy} onClick={props.onOpenPhoto}>Заменить</button>
        </div>
      )}
      <PrimaryButton
        disabled={busy || (props.consentRequired && props.parentHandoff && !props.adultConfirmed)}
        icon={<CameraUploadIcon />}
        onClick={primaryAction}
      >
        {primaryLabel}
      </PrimaryButton>
      {props.consentRequired && props.parentHandoff && (
        <button className="workbook-text-action" type="button" disabled={busy} onClick={() => props.onParentHandoff(false)}>Вернуть ребёнку</button>
      )}
      {props.pendingPhoto && !props.consentRequired && (
        <button className="workbook-text-action" type="button" disabled={busy} onClick={props.onClearPhoto}>Убрать выбранное фото</button>
      )}
      <SecondaryActions props={props} helpLabel="Не знаю, как решать" />
    </div>
  )
}

function SecondaryActions({ props, helpLabel }: { props: ActionComposerProps; helpLabel?: string }) {
  const helpAvailable = isTaskStep(props.step) && props.step.help_available
  return (
    <div className="workspace-secondary-actions" data-testid="workspace-secondary-actions">
      {helpAvailable && helpLabel && (
        <button type="button" disabled={props.busy} onClick={() => void props.journey.askForHelp(props.step.problem.id)}>{helpLabel}</button>
      )}
      {props.canTutor && <TutorTrigger props={props} />}
    </div>
  )
}

function TutorTrigger({ props }: { props: ActionComposerProps }) {
  return (
    <button
      ref={props.tutorTriggerRef}
      type="button"
      data-testid="tutor-trigger"
      aria-expanded="false"
      aria-controls={props.tutorId}
      disabled={props.busy}
      onClick={props.onOpenTutor}
    >
      Спросить AI-помощника
    </button>
  )
}

function PrimaryButton({
  children,
  type = 'button',
  disabled,
  icon,
  onClick,
}: {
  children: string
  type?: 'button' | 'submit'
  disabled?: boolean
  icon?: ReactNode
  onClick?: () => void
}) {
  return (
    <button
      type={type}
      className="workbook-primary-action"
      data-primary-action
      data-testid="workbook-primary-action"
      disabled={disabled}
      onClick={onClick}
    >
      <span>{icon}{children}</span><LongArrowRightIcon />
    </button>
  )
}

function retryLabel(code: string | undefined): boolean {
  return ['ai_unavailable', 'offline', 'http_429', 'request_failed'].includes(code ?? '')
}

function TutorSheet({
  id,
  titleId,
  sheetRef,
  inputRef,
  historyRef,
  statement,
  draft,
  history,
  status,
  error,
  onDraft,
  onSubmit,
  onClose,
  onKeyDown,
}: {
  id: string
  titleId: string
  sheetRef: RefObject<HTMLElement | null>
  inputRef: RefObject<HTMLTextAreaElement | null>
  historyRef: RefObject<HTMLDivElement | null>
  statement: string
  draft: string
  history: TutorMessage[]
  status: TutorStatus
  error: string | null
  onDraft: (value: string) => void
  onSubmit: (event: FormEvent) => void
  onClose: () => void
  onKeyDown: (event: KeyboardEvent<HTMLElement>) => void
}) {
  return (
    <div
      className="tutor-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <aside
        ref={sheetRef}
        id={id}
        className="tutor-sheet"
        data-testid="tutor-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={onKeyDown}
      >
        <div className="tutor-sheet__handle" aria-hidden />
        <header className="tutor-sheet__header">
          <div>
            <span>AI-помощник</span>
            <h2 id={titleId}>Разберём мысль, не ответ</h2>
          </div>
          <button type="button" data-testid="tutor-close" onClick={onClose} aria-label="Закрыть помощника"><CloseIcon /></button>
        </header>
        <div className="tutor-sheet__task" aria-label="Условие текущей задачи">
          <span>Сейчас решаем</span>
          <MathText text={statement} />
        </div>
        <div ref={historyRef} className="tutor-sheet__history" aria-label="Диалог с помощником">
          {history.length === 0 && (
            <p className="tutor-message tutor-message--assistant">Спроси о конкретном месте: что непонятно в условии, почему не сходится действие или как проверить свою мысль.</p>
          )}
          {history.map((message, index) => (
            <p key={`${message.role}-${index}`} className={`tutor-message tutor-message--${message.role}`}>{message.content}</p>
          ))}
          {status === 'sending' && <p className="tutor-message tutor-message--assistant tutor-message--thinking">Смотрю на твою задачу…</p>}
        </div>
        {error && <p className="workbook-inline-error" role="alert">{error}</p>}
        <form className="tutor-sheet__form" onSubmit={onSubmit}>
          <label htmlFor={`${id}-input`}>Твой вопрос</label>
          <textarea
            ref={inputRef}
            id={`${id}-input`}
            data-testid="tutor-question-input"
            value={draft}
            rows={2}
            maxLength={500}
            disabled={status === 'sending'}
            placeholder="Например: почему здесь нужно сравнить с половиной?"
            onChange={(event) => onDraft(event.target.value)}
          />
          <button type="submit" data-testid="tutor-send" disabled={status === 'sending' || !draft.trim()}>
            {status === 'error' ? 'Повторить' : 'Отправить вопрос'}<LongArrowRightIcon />
          </button>
        </form>
        <button type="button" className="tutor-sheet__return" onClick={onClose}>Вернуться к задаче</button>
      </aside>
    </div>
  )
}

function MasterySummary({ mastery }: { mastery: NonNullable<PhotoFeedbackStep['mastery']> }) {
  const probability = Math.round(mastery.value * 100)
  const evidence = mastery.evidence
  return (
    <div className="workbook-mastery" aria-label="Доказательства навыка">
      <span>Самостоятельные решения</span>
      <strong>{evidence ? `${evidence.correct}/${evidence.required_correct}` : `${probability}%`}</strong>
      <p>{mastery.reached ? 'Навык подтверждён' : evidence ? `Осталось новых решений: ${evidence.remaining_correct}` : `Порог темы ${Math.round(mastery.threshold * 100)}%`}</p>
    </div>
  )
}
