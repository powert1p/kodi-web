import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { ApTextField } from '../../components/ApTextField'
import { BrandMark } from '../../components/BrandMark'
import { MathText } from '../../components/MathText'
import { hasJourneyWorkspace } from '../../lib/journeyApi'
import type {
  DiagnosticQuestionStep,
  DiagnosticSkill,
  ExamMapStep,
  GuidedStep,
  JourneyNextStep,
  JourneyMastery,
  JourneyProfile,
  JourneyProfileInput,
  JourneyState,
  JourneyTopic,
  PhotoFeedbackStep,
  PhotoRecoveryStep,
  PhotoTaskStep,
  ProfileStep,
} from '../../lib/journeyApi'
import { useJourney, type JourneyIssue } from './useJourney'
import { LearningWorkspace } from './LearningWorkspace'
import './JourneyPage.css'

const MAX_PHOTO_BYTES = 8 * 1024 * 1024
const ACCEPTED_PHOTO_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'])

export interface PendingPhoto {
  identity: string
  problemId: number
  file: File
  attemptId: string
}

function clientAttemptId(): string {
  const id = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `photo-${id}`.slice(0, 64)
}

function currentProblemId(step: JourneyNextStep): number | null {
  return 'problem' in step ? step.problem.id : null
}

function stageLabel(type: JourneyNextStep['type']): string {
  if (type === 'profile' || type === 'exam_map') return 'Настройка'
  if (type.startsWith('diagnostic')) return 'Диагностика'
  if (type === 'route_ready') return 'Твой маршрут'
  if (type === 'route_complete') return 'Маршрут пройден'
  if (type === 'guided_step') return 'Разбор'
  if (type === 'transfer_task' || type === 'transfer_feedback') return 'Перенос'
  if (type === 'topic_result') return 'Результат'
  return 'Самостоятельно'
}

function preservesPracticePosition(type: JourneyNextStep['type']): boolean {
  return [
    'independent_task',
    'typed_processing',
    'guided_processing',
    'photo_processing',
    'photo_feedback',
    'photo_recovery',
    'guided_step',
    'transfer_task',
    'transfer_feedback',
  ].includes(type)
}

function focusHeadingAtStart(heading: HTMLElement | null) {
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
  heading?.focus({ preventScroll: true })
}

export function JourneyPage() {
  const journey = useJourney()
  const mainRef = useRef<HTMLDivElement>(null)
  const [pendingPhoto, setPendingPhoto] = useState<PendingPhoto | null>(null)
  const activeWorkspace = journey.state ? hasJourneyWorkspace(journey.state) : false
  const preservePracticePosition = journey.state ? preservesPracticePosition(journey.state.next_step.type) : false

  useLayoutEffect(() => {
    if (activeWorkspace || preservePracticePosition) return
    focusHeadingAtStart(mainRef.current?.querySelector<HTMLElement>('h1') ?? null)
  }, [activeWorkspace, preservePracticePosition, journey.state?.revision, journey.isLoading, journey.loadError?.code])

  useEffect(() => {
    setPendingPhoto(null)
  }, [journey.identity, journey.state?.journey_id])

  useEffect(() => {
    if (!journey.state || !pendingPhoto) return
    const problemId = currentProblemId(journey.state.next_step)
    const shouldClear = (
      (problemId !== null && problemId !== pendingPhoto.problemId)
      || ['photo_feedback', 'transfer_feedback', 'topic_result', 'route_complete'].includes(journey.state.next_step.type)
    )
    if (shouldClear) {
      setPendingPhoto((current) => current?.attemptId === pendingPhoto.attemptId ? null : current)
    }
  }, [journey.state, pendingPhoto])

  return (
    <div className={`journey-shell${activeWorkspace ? ' journey-shell--workspace' : ''}`}>
      {!activeWorkspace && <header className="journey-header">
        <BrandMark />
        <span className="journey-header__state" aria-live="polite">
          {journey.state ? stageLabel(journey.state.next_step.type) : 'Подготовка к NIS'}
        </span>
      </header>}
      <div ref={mainRef} className="journey-main" aria-busy={journey.pendingAction !== null}>
        {journey.isLoading && <LoadingScreen />}
        {!journey.isLoading && !journey.state && (
          <LoadErrorScreen issue={journey.loadError} onRetry={() => void journey.refresh()} />
        )}
        {journey.state && (
          <JourneyScreen
            journey={journey}
            state={journey.state}
            pendingPhoto={pendingPhoto}
            setPendingPhoto={setPendingPhoto}
          />
        )}
      </div>
    </div>
  )
}

type JourneyController = ReturnType<typeof useJourney>

function JourneyScreen({
  journey,
  state,
  pendingPhoto,
  setPendingPhoto,
}: {
  journey: JourneyController
  state: JourneyState
  pendingPhoto: PendingPhoto | null
  setPendingPhoto: (photo: PendingPhoto | null) => void
}) {
  const step = state.next_step
  if (hasJourneyWorkspace(state)) {
    return (
      <LearningWorkspace
        journey={journey}
        state={state}
        pendingPhoto={pendingPhoto?.identity === journey.identity && pendingPhoto.problemId === state.task.problem_id ? pendingPhoto : null}
        onPhoto={(file) => setPendingPhoto({ identity: journey.identity, problemId: state.task.problem_id, file, attemptId: clientAttemptId() })}
        onClearPhoto={() => setPendingPhoto(null)}
      />
    )
  }
  let content: ReactNode

  switch (step.type) {
    case 'profile':
      content = (
        <ProfileScreen
          step={step}
          busy={journey.pendingAction !== null}
          onSaveDraft={journey.saveProfileDraft}
          onSubmit={journey.saveProfile}
        />
      )
      break
    case 'exam_map':
      content = (
        <ExamMapScreen
          step={step}
          state={state}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('open_diagnostic_intro')}
        />
      )
      break
    case 'diagnostic_intro':
      content = (
        <DiagnosticIntroScreen
          step={step}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('start_diagnostic')}
        />
      )
      break
    case 'diagnostic_question':
      content = (
        <DiagnosticQuestionScreen
          key={step.question.id}
          step={step}
          busy={journey.pendingAction !== null}
          onSubmit={journey.answerDiagnostic}
        />
      )
      break
    case 'diagnostic_result':
      content = (
        <DiagnosticResultScreen
          step={step}
          routeTopics={state.context.route.topics}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('show_route')}
        />
      )
      break
    case 'route_ready':
      content = (
        <RouteScreen
          topics={step.topics}
          profile={state.context.profile}
          skillProfile={state.context.route.skill_profile}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('start_lesson')}
          onRetry={() => journey.refresh()}
        />
      )
      break
    case 'lesson_intro':
      content = (
        <LessonIntroScreen
          step={step}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('start_task')}
        />
      )
      break
    case 'independent_task':
    case 'transfer_task':
      content = (
        <PhotoTaskScreen
          step={step}
          issue={journey.issue}
          pendingAction={journey.pendingAction}
          pendingPhoto={pendingPhoto?.identity === journey.identity && pendingPhoto.problemId === step.problem.id ? pendingPhoto : null}
          onPhoto={(file) => setPendingPhoto({ identity: journey.identity, problemId: step.problem.id, file, attemptId: clientAttemptId() })}
          onUpload={(photo) => journey.uploadPhoto(step.problem.id, photo.file, state.revision, photo.attemptId)}
          onGrantConsent={journey.grantPhotoConsent}
          onHelp={() => journey.askForHelp(step.problem.id)}
        />
      )
      break
    case 'typed_processing':
    case 'guided_processing':
    case 'photo_processing':
      content = (
        <ProcessingScreen
          step={step}
          issue={journey.loadError}
          isFetching={journey.isFetching}
          onRefresh={() => journey.refresh()}
        />
      )
      break
    case 'guided_step':
      content = (
        <GuidedScreen
          key={`${step.problem.id}-${step.step.number}`}
          step={step}
          busy={journey.pendingAction !== null}
          onSubmit={journey.answerGuided}
        />
      )
      break
    case 'photo_feedback':
    case 'transfer_feedback':
      content = (
        <FeedbackScreen
          step={step}
          busy={journey.pendingAction !== null}
          onHelp={step.help_available ? () => journey.continueWith('review_with_help') : undefined}
          onContinue={() => journey.continueWith(
            step.verdict === 'correct'
              ? step.type === 'photo_feedback'
                ? 'start_transfer'
                : step.mastery?.reached === false ? 'continue_transfer' : 'finish_topic'
              : 'retry_task',
          )}
        />
      )
      break
    case 'photo_recovery':
      content = (
        <RecoveryScreen
          step={step}
          busy={journey.pendingAction !== null}
          onContinue={async () => {
            if (step.reason === 'provider_error') {
              await journey.retryPhoto()
            } else {
              setPendingPhoto(null)
              await journey.continueWith('retry_photo')
            }
          }}
        />
      )
      break
    case 'topic_result':
      content = (
        <TopicResultScreen
          step={step}
          busy={journey.pendingAction !== null}
          onContinue={() => journey.continueWith('next_lesson')}
        />
      )
      break
    case 'route_complete':
      content = <RouteCompleteScreen step={step} topics={state.context.route.topics} />
      break
  }

  return (
    <>
      {content}
      {journey.issue
        && journey.issue.code !== 'consent_required'
        && (
          journey.issue.status === 409
          || !['independent_task', 'transfer_task'].includes(step.type)
        )
        && (
        <GlobalIssue
          issue={journey.issue}
          onDismiss={journey.clearIssue}
          onRefresh={() => void journey.refresh()}
        />
      )}
    </>
  )
}

function ProfileScreen({ step, busy, onSaveDraft, onSubmit }: {
  step: ProfileStep
  busy: boolean
  onSaveDraft: (
    profile: JourneyProfileInput,
    screen: 0 | 1 | 2 | 3,
    substep?: 0 | 1 | 2,
  ) => Promise<JourneyState | null>
  onSubmit: (profile: JourneyProfileInput) => Promise<JourneyState | null>
}) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const screen = step.screen
  const [weeklyGoal, setWeeklyGoal] = useState(step.draft.weekly_goal)
  const [sessionMinutes, setSessionMinutes] = useState<20 | 30 | 45>(step.draft.session_minutes)
  const [targetWindow, setTargetWindow] = useState<JourneyProfile['target_window']>(step.draft.target_window)
  const [prepExperience, setPrepExperience] = useState<JourneyProfile['prep_experience']>(step.draft.prep_experience)
  const [weakTopics, setWeakTopics] = useState<string[]>(step.draft.weak_topics)
  const [strongTopics, setStrongTopics] = useState<string[]>(step.draft.strong_topics)
  const [mockMathBand, setMockMathBand] = useState<JourneyProfile['mock_math_band']>(step.draft.mock_math_band)
  const [rhythmQuestion, setRhythmQuestion] = useState<0 | 1 | 2>(step.substep)

  useLayoutEffect(() => {
    focusHeadingAtStart(headingRef.current)
  }, [screen, rhythmQuestion])

  useEffect(() => {
    setWeeklyGoal(step.draft.weekly_goal)
    setSessionMinutes(step.draft.session_minutes)
    setTargetWindow(step.draft.target_window)
    setPrepExperience(step.draft.prep_experience)
    setWeakTopics(step.draft.weak_topics)
    setStrongTopics(step.draft.strong_topics)
    setMockMathBand(step.draft.mock_math_band)
    setRhythmQuestion(step.substep)
  }, [step.draft, step.screen, step.substep])

  const topics = [
    { id: 'FR05', title: 'Дроби' },
    { id: 'PC05', title: 'Проценты' },
    { id: 'EQ04', title: 'Текстовые уравнения' },
    { id: 'GE04', title: 'Геометрические отношения' },
    { id: 'DA02', title: 'Графики и данные' },
  ]
  const setTopicStatus = (id: string, status: 'weak' | 'strong' | 'neutral') => {
    const nextWeak = weakTopics.filter((topicId) => topicId !== id)
    const nextStrong = strongTopics.filter((topicId) => topicId !== id)
    if (status === 'weak' && nextWeak.length < 3) nextWeak.push(id)
    if (status === 'strong' && nextStrong.length < 3) nextStrong.push(id)
    setWeakTopics(nextWeak)
    setStrongTopics(nextStrong)
  }
  const profile = (): JourneyProfileInput => ({
    weekly_goal: weeklyGoal,
    session_minutes: sessionMinutes,
    target_window: targetWindow,
    prep_experience: prepExperience,
    weak_topics: weakTopics,
    strong_topics: strongTopics,
    mock_math_band: mockMathBand,
  })
  const navigate = (nextScreen: 0 | 1 | 2 | 3, nextSubstep: 0 | 1 | 2 = 0) => (
    onSaveDraft(profile(), nextScreen, nextSubstep)
  )
  const submit = () => onSubmit(profile())

  const headings = [step.title, 'Выберем спокойный ритм', 'Что учесть в диагностике', 'Есть результат пробника?']
  const leads = [
    step.description,
    'Настроим нагрузку, которую реально выдерживать из недели в неделю.',
    'Для каждой темы выбери один статус. Самооценка только поменяет порядок вопросов.',
    'Если пробника не было — это нормально. Уровень всё равно определят ответы диагностики.',
  ]
  const proof = [
    ['Цель уже зафиксирована', 'Готовимся к поступлению в 7 класс. После настройки покажем всю карту подготовки.'],
    ['Ритм можно менять', 'Это твой план занятий, а не обещание результата или искусственный таймер.'],
    ['Самооценка — не оценка', 'Мы всё проверим короткой диагностикой и не запишем ответы о себе как освоенный навык.'],
    ['Пробник не обязателен', 'Он помогает понять контекст, но не заменяет доказательство навыка в диагностике.'],
  ] as const
  const currentProof = proof[screen] ?? proof[0]

  return (
    <section className="journey-form-screen">
      <div className="journey-form-card">
        <div className="profile-progress" aria-label={`Шаг ${screen + 1} из ${step.screen_count}`}>
          {[0, 1, 2, 3].map((index) => <span key={index} className={index <= screen ? 'is-active' : ''} />)}
        </div>
        <Eyebrow>Адаптация · {screen + 1} из {step.screen_count}</Eyebrow>
        <h1 ref={headingRef} tabIndex={-1}>{headings[screen]}</h1>
        <p className="journey-lead">{leads[screen]}</p>

        {screen === 0 && (
          <>
            <div className="goal-lock" aria-label="Цель подготовки">
              <span>Твоя цель</span>
              <strong>NIS · поступление в 7 класс</strong>
              <small>
                <span>{step.student.name}, {step.student.grade ? `${step.student.grade} класс` : 'класс уточним позже'}</span>
                <span>Обучение на русском</span>
              </small>
            </div>
            <fieldset className="profile-field">
              <legend>Когда планируешь поступать?</legend>
              <p>Если дата изменится, маршрут можно будет перенастроить.</p>
              <div className="choice-grid choice-grid--two">
                <ChoiceRadio name="target-window" label="Весна 2027" detail="Ближайший набор" checked={targetWindow === 'spring-2027'} onChange={() => setTargetWindow('spring-2027')} />
                <ChoiceRadio name="target-window" label="Позже — без спешки" detail="Больше времени на базу" checked={targetWindow === 'later'} onChange={() => setTargetWindow('later')} />
              </div>
            </fieldset>
            <ApButton full size="l" loading={busy} onClick={() => void navigate(1)}>Продолжить к ритму<ArrowIcon /></ApButton>
          </>
        )}

        {screen === 1 && (
          <>
            <p className="profile-question-counter">Ритм · {rhythmQuestion + 1} из 3</p>
            {rhythmQuestion === 0 && (
              <fieldset className="profile-field">
                <legend>Сколько занятий в неделю реально выдерживать?</legend>
                <div className="choice-grid choice-grid--three">
                  {[3, 4, 5].map((value) => (
                    <ChoiceRadio key={value} name="weekly-goal" label={`${value} раза`} detail="в неделю" checked={weeklyGoal === value} onChange={() => setWeeklyGoal(value)} />
                  ))}
                </div>
              </fieldset>
            )}
            {rhythmQuestion === 1 && (
              <fieldset className="profile-field">
                <legend>Сколько времени удобно заниматься за раз?</legend>
                <div className="choice-grid choice-grid--three">
                  {([20, 30, 45] as const).map((value) => (
                    <ChoiceRadio key={value} name="session-minutes" label={`${value} минут`} detail="за занятие" checked={sessionMinutes === value} onChange={() => setSessionMinutes(value)} />
                  ))}
                </div>
              </fieldset>
            )}
            {rhythmQuestion === 2 && (
              <fieldset className="profile-field">
                <legend>Как ты готовился раньше?</legend>
                <div className="choice-grid choice-grid--three">
                  <ChoiceRadio name="prep-experience" label="С нуля" detail="ещё не готовился" checked={prepExperience === 'new'} onChange={() => setPrepExperience('new')} />
                  <ChoiceRadio name="prep-experience" label="Сам" detail="готовился самостоятельно" checked={prepExperience === 'self'} onChange={() => setPrepExperience('self')} />
                  <ChoiceRadio name="prep-experience" label="С учителем" detail="были занятия" checked={prepExperience === 'teacher'} onChange={() => setPrepExperience('teacher')} />
                </div>
              </fieldset>
            )}
            <div className="profile-actions">
              <button
                type="button"
                className="profile-back"
                disabled={busy}
                onClick={() => rhythmQuestion === 0
                  ? void navigate(0)
                  : void navigate(1, (rhythmQuestion - 1) as 0 | 1)}
              >
                Назад
              </button>
              {rhythmQuestion < 2 ? (
                <ApButton size="l" loading={busy} onClick={() => void navigate(1, (rhythmQuestion + 1) as 1 | 2)}>Дальше<ArrowIcon /></ApButton>
              ) : (
                <ApButton size="l" loading={busy} onClick={() => void navigate(2)}>Продолжить к темам<ArrowIcon /></ApButton>
              )}
            </div>
          </>
        )}

        {screen === 2 && (
          <>
            <div className="topic-status-list" aria-label="Самооценка по темам">
              {topics.map((topic) => (
                <TopicStatusRow
                  key={topic.id}
                  id={topic.id}
                  title={topic.title}
                  value={weakTopics.includes(topic.id) ? 'weak' : strongTopics.includes(topic.id) ? 'strong' : 'neutral'}
                  weakDisabled={weakTopics.length >= 3 && !weakTopics.includes(topic.id)}
                  strongDisabled={strongTopics.length >= 3 && !strongTopics.includes(topic.id)}
                  onChange={(value) => setTopicStatus(topic.id, value)}
                />
              ))}
            </div>
            <p className="profile-hint">Не больше трёх сложных и трёх сильных тем. Можно оставить «Не уверен».</p>
            <div className="profile-actions">
              <button type="button" className="profile-back" disabled={busy} onClick={() => void navigate(1, 2)}>Назад</button>
              <ApButton size="l" loading={busy} onClick={() => void navigate(3)}>Продолжить<ArrowIcon /></ApButton>
            </div>
          </>
        )}

        {screen === 3 && (
          <>
            <fieldset className="profile-field">
              <legend>Решал пробный блок математики из 40 вопросов?</legend>
              <div className="choice-grid choice-grid--four">
                {([
                  ['not-taken', 'Не решал'],
                  ['0-20', '0–20 верных из 40'],
                  ['21-30', '21–30 верных из 40'],
                  ['31-40', '31–40 верных из 40'],
                ] as const).map(([value, label]) => (
                  <ChoiceRadio key={value} name="mock-math" label={label} checked={mockMathBand === value} onChange={() => setMockMathBand(value)} />
                ))}
              </div>
            </fieldset>
            <div className="profile-actions">
              <button type="button" className="profile-back" disabled={busy} onClick={() => void navigate(2)}>Назад</button>
              <ApButton size="l" loading={busy} onClick={() => void submit()}>Построить диагностику<ArrowIcon /></ApButton>
            </div>
          </>
        )}
      </div>
      <aside className="journey-form-proof" aria-label="Что будет дальше">
        <span className="proof-number">0{screen + 1}</span>
        <div>
          <b>{currentProof[0]}</b>
          <p>{currentProof[1]}</p>
        </div>
      </aside>
    </section>
  )
}

function TopicStatusRow({ id, title, value, weakDisabled, strongDisabled, onChange }: {
  id: string
  title: string
  value: 'weak' | 'strong' | 'neutral'
  weakDisabled: boolean
  strongDisabled: boolean
  onChange: (value: 'weak' | 'strong' | 'neutral') => void
}) {
  return (
    <fieldset className="topic-status-row">
      <legend>{title}</legend>
      <div>
        <label>
          <input type="radio" name={`topic-${id}`} aria-label={`${title}: сложно`} checked={value === 'weak'} disabled={weakDisabled} onChange={() => onChange('weak')} />
          <span>Сложно</span>
        </label>
        <label>
          <input type="radio" name={`topic-${id}`} aria-label={`${title}: не уверен`} checked={value === 'neutral'} onChange={() => onChange('neutral')} />
          <span>Не уверен</span>
        </label>
        <label>
          <input type="radio" name={`topic-${id}`} aria-label={`${title}: получается`} checked={value === 'strong'} disabled={strongDisabled} onChange={() => onChange('strong')} />
          <span>Получается</span>
        </label>
      </div>
    </fieldset>
  )
}

function ChoiceRadio({ name, label, detail, checked, onChange }: {
  name: string
  label: string
  detail?: string
  checked: boolean
  onChange: () => void
}) {
  return (
    <label className="choice-control">
      <input type="radio" name={name} aria-label={label} checked={checked} onChange={onChange} />
      <span><b>{label}</b>{detail && <small>{detail}</small>}</span>
    </label>
  )
}

function ExamMapScreen({ step, state, busy, onContinue }: {
  step: ExamMapStep
  state: JourneyState
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
}) {
  const examMap = state.context.exam_map
  return (
    <section className="journey-map-screen">
      <div className="journey-copy-column">
        <Eyebrow>Формат отбора · цикл {examMap.cycle ?? '2026–2027'}</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">Сначала покажем, к чему готовимся. В маршруте нет случайных упражнений.</p>
        <div className="scope-note"><InfoIcon /><span>{step.scope_note}</span></div>
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>
          {step.primary_action}<ArrowIcon />
        </ApButton>
        {(examMap.source_note || examMap.disclaimer) && (
          <details className="exam-source-note">
            <summary>Источник и актуальность формата</summary>
            <div>
              {examMap.source_note && <p>{examMap.source_note}</p>}
              {examMap.disclaimer && <p>{examMap.disclaimer}</p>}
              {examMap.source_url && <a href={examMap.source_url} target="_blank" rel="noreferrer">Источник: NIS ↗</a>}
            </div>
          </details>
        )}
      </div>
      <ol className="exam-blocks">
        {state.context.exam_map.day_one.map((block, index) => (
          <li key={block.name} className={block.covered ? 'is-covered' : ''}>
            <span className="exam-blocks__index">0{index + 1}</span>
            <div><strong>{block.name}</strong><span>{block.questions} вопросов · {block.minutes} минут</span></div>
            <em>{block.covered ? 'в маршруте' : 'не входит'}</em>
          </li>
        ))}
      </ol>
    </section>
  )
}

function DiagnosticIntroScreen({ step, busy, onContinue }: {
  step: Extract<JourneyNextStep, { type: 'diagnostic_intro' }>
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
}) {
  return (
    <section className="diagnostic-intro">
      <ProgressLens value={String(step.estimated_minutes)} suffix="мин" label="примерное время" />
      <div className="diagnostic-intro__copy">
        <Eyebrow>Шаг 2 из 3 · адаптация</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">{step.description}</p>
        <ul className="quiet-checks">
          <li><CheckIcon />Проверим дроби, проценты, уравнения, геометрию и графики</li>
          <li><CheckIcon />Можно отвечать коротко — только число или выражение</li>
          <li><CheckIcon />Если навык пока сложный, вопрос станет проще</li>
          <li><CheckIcon />Ответы сохраняются — можно продолжить после перерыва</li>
        </ul>
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>
          {step.primary_action}<ArrowIcon />
        </ApButton>
      </div>
    </section>
  )
}

function DiagnosticQuestionScreen({ step, busy, onSubmit }: {
  step: DiagnosticQuestionStep
  busy: boolean
  onSubmit: (questionId: number, answer: string) => Promise<JourneyState | null>
}) {
  const [answer, setAnswer] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!answer.trim()) {
      setLocalError('Введи ответ, чтобы продолжить')
      return
    }
    void onSubmit(step.question.id, answer.trim())
  }
  const progress = Math.min(100, Math.round((step.progress.answered / Math.max(step.progress.planned, 1)) * 100))
  return (
    <section className="question-screen">
      <div className="question-progress" aria-label={`Вопрос ${step.progress.current}, отвечено ${step.progress.answered}`}>
        <div><span>Диагностика</span><strong>{step.progress.current} / {step.progress.planned}</strong></div>
        <div className="question-progress__track"><span style={{ width: `${progress}%` }} /></div>
      </div>
      <div className="question-card">
        <Eyebrow>Опорный вопрос</Eyebrow>
        <h1 tabIndex={-1}>Реши в уме или на черновике</h1>
        <div className="problem-statement"><MathText text={step.question.statement} /></div>
        <form onSubmit={submit} className="answer-form">
          <ApTextField
            label="Твой ответ"
            aria-label="Твой ответ"
            value={answer}
            onChange={(event) => { setAnswer(event.target.value); setLocalError(null) }}
            inputMode="decimal"
            autoComplete="off"
            fieldSize="l"
            error={localError}
            disabled={busy}
          />
          <ApButton type="submit" full size="l" loading={busy}>{step.primary_action}<ArrowIcon /></ApButton>
        </form>
      </div>
    </section>
  )
}

function DiagnosticResultScreen({ step, routeTopics, busy, onContinue }: {
  step: Extract<JourneyNextStep, { type: 'diagnostic_result' }>
  routeTopics: JourneyTopic[]
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
}) {
  const priority = step.skill_profile.find((skill) => skill.route_topic_id === routeTopics[0]?.id)
    ?? step.skill_profile.find((skill) => skill.level === 'foundation')
    ?? step.skill_profile.find((skill) => skill.level === 'developing')
    ?? step.skill_profile[0]
  return (
    <section className="result-transition">
      <ProgressLens value={String(step.score.correct)} suffix={`/${step.score.total}`} label="опорных задач" ratio={step.score.correct / Math.max(step.score.total, 1)} />
      <div>
        <Eyebrow>Диагностика завершена</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">{step.description}</p>
        {priority && (
          <div className="priority-skill" data-level={priority.level}>
            <span>Первая точка роста</span>
            <b>{priority.title}</b>
            <small>{priority.label}</small>
          </div>
        )}
        <div className="scope-note"><SparkIcon /><span><b>Это не оценка.</b> Ошибки определили порядок тем, а не твои способности.</span></div>
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>{step.primary_action}<ArrowIcon /></ApButton>
        <details className="skill-profile-disclosure">
          <summary>Показать профиль всех 5 навыков</summary>
          <ul className="skill-profile" aria-label="Профиль навыков по диагностике">
            {step.skill_profile.map((skill) => (
              <li key={skill.id} data-level={skill.level}>
                <span aria-hidden />
                <div><b>{skill.title}</b><small>{skill.label}</small></div>
              </li>
            ))}
          </ul>
        </details>
      </div>
    </section>
  )
}

function RouteScreen({ topics, profile, skillProfile, busy, onContinue, onRetry }: {
  topics: JourneyTopic[]
  profile?: JourneyProfile
  skillProfile?: DiagnosticSkill[]
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
  onRetry: () => Promise<unknown>
}) {
  const first = topics[0]
  const completed = topics.filter((topic) => topic.status === 'completed').length
  const secureSkills = skillProfile?.filter((skill) => skill.level === 'secure').length ?? 0
  if (!first) return <LoadErrorScreen issue={{ code: 'empty_route', message: 'Маршрут пока пуст. Обнови экран.', status: 0 }} onRetry={() => void onRetry()} />
  return (
    <section className="route-screen">
      <div className="route-orbit" aria-hidden />
      <ProgressLens value={String(completed)} suffix={`/${topics.length}`} label="тем пройдено" ratio={completed / topics.length} compact />
      <div className="route-copy">
        <Eyebrow>Твой маршрут · {first.strand}</Eyebrow>
        <h1 tabIndex={-1}>{first.title}</h1>
        <p className="journey-lead">{first.goal}</p>
        <div className="route-reason"><SparkIcon /><span><b>Почему начинаем здесь</b>{first.reason}</span></div>
        <div className="route-readiness" aria-label="Готовность по диагностике">
          <span>Опоры диагностики</span>
          <b>{secureSkills} из {skillProfile?.length ?? topics.length}</b>
          <small>Остальные навыки уже расставлены по приоритету</small>
        </div>
        {profile && (
          <div className="route-pace" aria-label="Выбранный ритм">
            <span>Твой ритм</span>
            <b>{profile.weekly_goal} занятия × {profile.session_minutes} минут</b>
            <small>{profile.target_window === 'spring-2027' ? 'цель — весна 2027' : 'срок без спешки'}</small>
          </div>
        )}
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>Начать первую тему<ArrowIcon /></ApButton>
      </div>
      <ol className="route-switcher" aria-label="Персональный маршрут">
        {topics.map((topic, index) => (
          <li key={topic.id} className={index === 0 ? 'is-active' : ''}>
            <span>{index === 0 ? 'Сейчас' : `Дальше ${index}`}</span><b>{topic.title}</b>
          </li>
        ))}
      </ol>
    </section>
  )
}

function LessonIntroScreen({ step, busy, onContinue }: {
  step: Extract<JourneyNextStep, { type: 'lesson_intro' }>
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
}) {
  return (
    <section className="lesson-transition">
      <div className="lesson-transition__number">01</div>
      <div className="lesson-transition__copy">
        <Eyebrow>{step.topic.strand} · первая тема</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">{step.goal}</p>
        <div className="route-reason"><SparkIcon /><span><b>Почему сейчас</b>{step.description}</span></div>
        <div className="lesson-contract">
          <span>Как работаем</span>
          <p>Сначала решаешь задачу целиком на бумаге. Разбор включится только если сам попросишь.</p>
        </div>
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>{step.primary_action}<ArrowIcon /></ApButton>
      </div>
    </section>
  )
}

function PhotoTaskScreen({
  step,
  issue,
  pendingAction,
  pendingPhoto,
  onPhoto,
  onUpload,
  onGrantConsent,
  onHelp,
}: {
  step: PhotoTaskStep
  issue: JourneyIssue | null
  pendingAction: string | null
  pendingPhoto: PendingPhoto | null
  onPhoto: (file: File) => void
  onUpload: (photo: PendingPhoto) => Promise<JourneyState | null>
  onGrantConsent: () => Promise<JourneyState | null>
  onHelp: () => Promise<JourneyState | null>
}) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const parentTitleRef = useRef<HTMLHeadingElement>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [parentHandoff, setParentHandoff] = useState(false)
  const [adultConfirmed, setAdultConfirmed] = useState(false)
  const busy = pendingAction !== null
  useEffect(() => {
    if (parentHandoff) parentTitleRef.current?.focus({ preventScroll: true })
  }, [parentHandoff])
  function selectFile(file: File | undefined) {
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
  const consentRequired = step.photo_consent_required || issue?.code === 'consent_required'
  if (consentRequired && parentHandoff) {
    return (
      <section className="parent-consent-screen">
        <div className="consent-parent-panel">
          <span className="consent-gate__icon"><ShieldIcon /></span>
          <Eyebrow>Для родителя или законного представителя</Eyebrow>
          <h1 ref={parentTitleRef} tabIndex={-1}>Разрешение на проверку фото</h1>
          <p>AiPlus использует снимок решения только для проверки хода вычислений и обратной связи ребёнку.</p>
          <label className="consent-confirmation">
            <input
              type="checkbox"
              checked={adultConfirmed}
              onChange={(event) => setAdultConfirmed(event.target.checked)}
            />
            <span>Я родитель или законный представитель и разрешаю использовать фото решения для проверки.</span>
          </label>
          {issue && issue.code !== 'consent_required' && issue.status !== 409 && <InlineIssue issue={issue} />}
          <ApButton
            full
            size="l"
            loading={pendingAction === 'consent'}
            disabled={!adultConfirmed || busy}
            onClick={() => void onGrantConsent()}
          >
            Разрешить проверку фото<CheckIcon />
          </ApButton>
          <button className="quiet-action quiet-action--parent" type="button" disabled={busy} onClick={() => setParentHandoff(false)}>
            Вернуть ребёнку
          </button>
        </div>
      </section>
    )
  }
  return (
    <section className="task-screen">
      <ModeMark transfer={step.type === 'transfer_task'} />
      <div className="task-copy">
        <Eyebrow>{step.problem.topic.title} · {step.type === 'transfer_task' ? 'новая задача' : 'самостоятельно'}</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <div className="problem-statement problem-statement--large"><MathText text={step.problem.statement} /></div>
        <p className="task-instruction"><CameraIcon />{step.instruction}</p>

        {consentRequired ? (
          <div className="consent-gate">
            <span className="consent-gate__icon"><ShieldIcon /></span>
            <div>
              <b>Позови родителя на один шаг</b>
              <p>Взрослый разрешит использовать фото только для проверки решения. Сам снимок после этого отправишь ты.</p>
            </div>
            <ApButton full size="l" onClick={() => setParentHandoff(true)}>
              Передать взрослому<ArrowIcon />
            </ApButton>
            {issue && issue.code !== 'consent_required' && issue.status !== 409 && <InlineIssue issue={issue} />}
          </div>
        ) : (
          <div className="photo-actions" aria-busy={pendingAction === 'photo'}>
            <input
              ref={inputRef}
              id={inputId}
              className="sr-only"
              tabIndex={-1}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif"
              capture="environment"
              aria-label="Фото всего решения"
              disabled={busy}
              onChange={(event) => {
                selectFile(event.target.files?.[0])
                event.currentTarget.value = ''
              }}
            />
            {pendingPhoto ? (
              <>
                <div className="selected-photo" aria-live="polite">
                  <CheckIcon />
                  <span><b>{pendingPhoto.file.name}</b>{formatFileSize(pendingPhoto.file.size)} · вся страница</span>
                  <button
                    type="button"
                    className="selected-photo__replace"
                    disabled={busy}
                    onClick={() => inputRef.current?.click()}
                  >
                    Заменить
                  </button>
                </div>
                <ApButton full size="l" loading={pendingAction === 'photo'} disabled={busy} onClick={() => void onUpload(pendingPhoto)}>
                  <CameraIcon />Отправить решение
                </ApButton>
              </>
            ) : (
              <button
                type="button"
                className="photo-picker"
                disabled={busy}
                onClick={() => inputRef.current?.click()}
              >
                <CameraIcon /><span><b>{step.primary_action}</b><small>Сними лист целиком при хорошем свете</small></span>
              </button>
            )}
            {fileError && <p className="field-error" role="alert">{fileError}</p>}
            {issue && issue.code !== 'consent_required' && issue.status !== 409 && <InlineIssue issue={issue} />}
          </div>
        )}

        {step.help_available && (
          <button className="quiet-action" type="button" disabled={busy} onClick={() => void onHelp()}>
            Не знаю, как решать
          </button>
        )}
      </div>
    </section>
  )
}

function GuidedScreen({ step, busy, onSubmit }: {
  step: GuidedStep
  busy: boolean
  onSubmit: (problemId: number, stepNumber: number, answer: string) => Promise<JourneyState | null>
}) {
  const [answer, setAnswer] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!answer.trim()) {
      setLocalError('Введи ответ этого шага')
      return
    }
    void onSubmit(step.problem.id, step.step.number, answer.trim())
  }
  return (
    <section className="task-screen task-screen--guided">
      <ProgressLens value={String(step.step.number)} suffix={`/${step.step.total}`} label="шаг разбора" ratio={step.step.number / Math.max(step.step.total, 1)} compact />
      <div className="task-copy">
        <Eyebrow>Та же задача · без фото на шагах</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <details className="problem-disclosure">
          <summary>Показать условие той же задачи</summary>
          <div><MathText text={step.problem.statement} /></div>
        </details>
        <div className="guided-prompt">
          <span>Шаг {step.step.number}</span>
          <p><MathText text={step.step.instruction} /></p>
        </div>
        <div className="mastery-note"><InfoIcon /><span>{step.mastery_note}</span></div>
        {step.feedback && (
          <p className={`guided-feedback ${step.feedback.verdict === 'correct' ? 'is-correct' : ''}`} role="status">
            {step.feedback.message}
          </p>
        )}
        <form onSubmit={submit} className="answer-form answer-form--guided">
          <ApTextField
            label="Ответ шага"
            aria-label="Ответ шага"
            value={answer}
            onChange={(event) => { setAnswer(event.target.value); setLocalError(null) }}
            inputMode="decimal"
            autoComplete="off"
            fieldSize="l"
            error={localError}
            disabled={busy}
          />
          <ApButton type="submit" full size="l" loading={busy}>{step.primary_action}<ArrowIcon /></ApButton>
        </form>
      </div>
    </section>
  )
}

function FeedbackScreen({ step, busy, onContinue, onHelp }: {
  step: PhotoFeedbackStep
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
  onHelp?: () => Promise<JourneyState | null>
}) {
  const correct = step.verdict === 'correct'
  return (
    <section className={`feedback-screen ${correct ? 'is-correct' : 'is-correction'}`}>
      <div className="feedback-signal" aria-hidden>{correct ? <CheckIcon /> : <PencilIcon />}</div>
      <div className="feedback-copy">
        <Eyebrow>{correct ? 'Решение проверено' : `Расхождение · шаг ${step.failed_step ?? ''}`}</Eyebrow>
        <h1 tabIndex={-1}>{correct ? 'Ход решения сошёлся' : 'Исправь одно место'}</h1>
        <p className="journey-lead">{step.message}</p>
        {!correct && step.confirmed_steps && step.confirmed_steps.length > 0 && (
          <div className="confirmed-reasoning">
            <span><CheckIcon />До ошибки верно</span>
            <ol>
              {step.confirmed_steps.map((item) => <li key={item.number}>{item.label}</li>)}
            </ol>
          </div>
        )}
        {!correct && step.correction && (
          <div className="correction-focus">
            <span>Первое расхождение · шаг {step.failed_step}</span>
            <p>Вернись к этому переходу и проверь действие, вычисление и единицы. Ответ пока не раскрываем.</p>
          </div>
        )}
        {step.mastery && (
          <MasteryEvidence mastery={step.mastery} />
        )}
        <div className="feedback-actions">
          <ApButton size="l" loading={busy} onClick={() => void onContinue()}>{step.primary_action}<ArrowIcon /></ApButton>
          {!correct && onHelp && (
            <button className="quiet-action" type="button" disabled={busy} onClick={() => void onHelp()}>
              Разобрать по шагам
            </button>
          )}
        </div>
      </div>
    </section>
  )
}

function masteryView(mastery: JourneyMastery) {
  const evidence = mastery.evidence
  const probability = Math.round(mastery.value * 100)
  const threshold = Math.round(mastery.threshold * 100)
  if (!evidence) {
    return {
      value: `${probability}`,
      suffix: '%',
      label: mastery.reached ? 'навык подтверждён' : 'устойчивость навыка',
      ratio: mastery.value,
      detail: `Порог самостоятельности ${threshold}%`,
    }
  }
  if (!evidence.correct_reached) {
    const remaining = evidence.remaining_correct
    return {
      value: `${evidence.correct}`,
      suffix: `/${evidence.required_correct}`,
      label: 'самостоятельных решений',
      ratio: evidence.correct / evidence.required_correct,
      detail: `${remaining === 1 ? 'Осталась 1 новая задача' : `Осталось новых задач: ${remaining}`} · уверенность ${probability}%`,
    }
  }
  if (!evidence.accuracy_reached) {
    const accuracy = Math.round((evidence.accuracy ?? 0) * 100)
    return {
      value: `${accuracy}`,
      suffix: '%',
      label: 'точность решений',
      ratio: evidence.accuracy ?? 0,
      detail: `Минимум ${Math.round(evidence.minimum_accuracy * 100)}% · подтверждений ${evidence.correct}/${evidence.required_correct}`,
    }
  }
  if (!evidence.probability_reached) {
    return {
      value: `${probability}`,
      suffix: '%',
      label: 'устойчивость навыка',
      ratio: mastery.value,
      detail: `Порог ${threshold}% · самостоятельных решений ${evidence.correct}`,
    }
  }
  return {
    value: `${evidence.correct}`,
    suffix: `/${evidence.required_correct}`,
    label: 'самостоятельных решений',
    ratio: 1,
    detail: `Уверенность ${probability}% · порог ${threshold}% пройден`,
  }
}

function MasteryEvidence({ mastery }: { mastery: JourneyMastery }) {
  const view = masteryView(mastery)
  return (
    <div className="mastery-evidence">
      <span>Доказательства навыка</span>
      <strong>{view.value}<i>{view.suffix}</i></strong>
      <small>{view.label}</small>
      <em>{view.detail}</em>
    </div>
  )
}

function RecoveryScreen({ step, busy, onContinue }: {
  step: PhotoRecoveryStep
  busy: boolean
  onContinue: () => Promise<void>
}) {
  const providerError = step.reason === 'provider_error'
  const title = providerError
    ? 'Проверка на паузе'
    : step.reason === 'wrong_photo'
      ? 'Это не решение задачи'
      : step.reason === 'unreadable'
        ? 'Не удалось прочитать запись'
        : 'Нужен более ясный снимок'
  return (
    <section className="recovery-screen">
      <div className="preserved-mark"><CameraIcon /><span><b>Фото сохранено</b>{providerError ? 'переснимать его не нужно' : 'математической ошибки не записано'}</span></div>
      <div className="recovery-copy">
        <Eyebrow>Проверка решения</Eyebrow>
        <h1 tabIndex={-1}>{title}</h1>
        <div className="recovery-alert" role="alert"><b>{step.message}</b><span>{recoveryHint(step.reason)}</span></div>
        <div className="photo-proof"><CheckIcon /><span><b>{step.preserved_photo.name}</b>предыдущая попытка сохранена</span></div>
        {providerError && (
          <p className="resume-note"><InfoIcon />После перезагрузки откроется сохранённое состояние. Повторную проверку запустим без математического штрафа.</p>
        )}
        <ApButton full size="l" loading={busy} onClick={() => void onContinue()}>
          {providerError ? <RefreshIcon /> : <CameraIcon />}{step.primary_action}
        </ApButton>
      </div>
    </section>
  )
}

function ProcessingScreen({ step, issue, isFetching, onRefresh }: {
  step: Extract<JourneyNextStep, { type: 'photo_processing' | 'typed_processing' | 'guided_processing' }>
  issue: JourneyIssue | null
  isFetching: boolean
  onRefresh: () => Promise<unknown>
}) {
  const typedProcessing = step.type === 'typed_processing'
  const guidedProcessing = step.type === 'guided_processing'
  const savedValue = step.type === 'photo_processing'
    ? step.preserved_photo.name
    : step.preserved_answer.value
  const savedLabel = step.type === 'photo_processing'
    ? 'снимок сохранён на сервере'
    : guidedProcessing
      ? 'ответ шага сохранён на сервере'
      : 'ответ сохранён на сервере'
  return (
    <section className="processing-screen" aria-live="polite">
      <div className="processing-lens" aria-hidden><span /></div>
      <div className="processing-copy">
        <Eyebrow>{guidedProcessing ? 'Шаг сохранён' : typedProcessing ? 'Ответ сохранён' : 'Фото получено'}</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">{step.message}</p>
        <div className="photo-proof"><CheckIcon /><span><b>{savedValue}</b> {savedLabel}</span></div>
        {issue && (
          <div className="processing-error" role="alert">
            <b>Не удалось обновить статус</b>
            <span>{issue.message} {step.type === 'photo_processing' ? 'Фото уже сохранено — повторная съёмка не нужна.' : 'Ответ уже сохранён — повторная отправка не нужна.'}</span>
          </div>
        )}
        <ApButton variant="secondary" size="l" loading={isFetching} onClick={() => void onRefresh()}><RefreshIcon />Проверить статус</ApButton>
      </div>
    </section>
  )
}

function TopicResultScreen({ step, busy, onContinue }: {
  step: Extract<JourneyNextStep, { type: 'topic_result' }>
  busy: boolean
  onContinue: () => Promise<JourneyState | null>
}) {
  const reached = step.mastery.reached
  const mastery = masteryView(step.mastery)
  return (
    <section className="result-transition result-transition--mastery">
      <ProgressLens
        value={mastery.value}
        suffix={mastery.suffix}
        label={reached ? 'навык подтверждён' : mastery.label}
        ratio={mastery.ratio}
      />
      <div>
        <Eyebrow>{step.topic.strand} · результат</Eyebrow>
        <h1 tabIndex={-1}>{step.title}</h1>
        <p className="journey-lead">
          {reached
            ? 'Ты применил способ в новой задаче без разбора. Именно это считается результатом.'
            : 'Решение сохранено, но навык ещё нужно подтвердить в новой самостоятельной задаче.'}
        </p>
        <div className={`route-reason ${reached ? '' : 'is-pending'}`}>
          {reached ? <CheckIcon /> : <InfoIcon />}
          <span>
            <b>{step.topic.title}</b>
            {mastery.detail}
          </span>
        </div>
        <ApButton size="l" loading={busy} onClick={() => void onContinue()}>{step.primary_action}<ArrowIcon /></ApButton>
      </div>
    </section>
  )
}

function RouteCompleteScreen({ step, topics }: {
  step: Extract<JourneyNextStep, { type: 'route_complete' }>
  topics: JourneyTopic[]
}) {
  return (
    <section className="route-complete">
      <span className="route-complete__check"><CheckIcon /></span>
      <Eyebrow>Результат сохранён</Eyebrow>
      <h1 tabIndex={-1}>{step.title}</h1>
      <p className="journey-lead">{step.description}</p>
      <ol>
        {topics.map((topic) => <li key={topic.id}><CheckIcon /><span><b>{topic.title}</b>{topic.goal}</span></li>)}
      </ol>
      <p className="route-complete__note">Следующая сессия начнётся с нового маршрута по подтверждённым результатам.</p>
      <Link className="route-complete__action" to="/analytics">{step.primary_action}<ArrowIcon /></Link>
    </section>
  )
}

function ModeMark({ transfer }: { transfer: boolean }) {
  return (
    <div className="mode-mark" aria-label={`Режим: ${transfer ? 'проверка переноса' : 'самостоятельное решение'}`}>
      <PencilIcon /><span><b>{transfer ? 'Новая задача' : 'Самостоятельно'}</b>{transfer ? 'подтверждает навык' : 'одно фото целого решения'}</span>
    </div>
  )
}

function ProgressLens({ value, suffix, label, ratio, compact = false }: {
  value: string
  suffix: string
  label: string
  ratio?: number
  compact?: boolean
}) {
  const progress = ratio === undefined ? null : Math.max(0, Math.min(1, ratio))
  const style = progress === null
    ? undefined
    : { '--lens-progress': `${progress * 360}deg` } as CSSProperties
  return (
    <div
      className={`progress-lens ${progress === null ? 'is-metric' : 'has-progress'} ${compact ? 'is-compact' : ''}`}
      style={style}
      aria-label={`${value}${suffix}: ${label}`}
    >
      <strong>{value}<small>{suffix}</small></strong><span>{label}</span>
    </div>
  )
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="journey-eyebrow">{children}</p>
}

function InlineIssue({ issue }: { issue: JourneyIssue }) {
  return <p className="inline-issue" role="alert"><InfoIcon />{issue.message}</p>
}

function GlobalIssue({
  issue,
  onDismiss,
  onRefresh,
}: {
  issue: JourneyIssue
  onDismiss: () => void
  onRefresh: () => void
}) {
  return (
    <div className="global-issue" role="alert" aria-live="assertive">
      <InfoIcon /><span>{issue.message}</span>
      <div className="global-issue__actions">
        {issue.status === 409 && (
          <button type="button" className="global-issue__reload" onClick={onRefresh}>
            Загрузить актуальный маршрут
          </button>
        )}
        <button
          type="button"
          className="global-issue__close"
          onClick={onDismiss}
          aria-label="Закрыть сообщение"
        >
          ×
        </button>
      </div>
    </div>
  )
}

function LoadingScreen() {
  return (
    <section className="journey-loading" role="status" aria-label="Загружаем твой маршрут">
      <div className="journey-loading__orb" />
      <span>Открываем твой маршрут…</span>
    </section>
  )
}

function LoadErrorScreen({ issue, onRetry }: { issue: JourneyIssue | null; onRetry: () => void }) {
  return (
    <section className="load-error">
      <Eyebrow>{issue?.code === 'offline' ? 'Нет соединения' : 'Маршрут не открылся'}</Eyebrow>
      <h1 tabIndex={-1}>Учёба никуда не пропала</h1>
      <p className="journey-lead">{issue?.message ?? 'Попробуй обновить экран. Прогресс хранится на сервере.'}</p>
      <ApButton size="l" onClick={onRetry}><RefreshIcon />Попробовать ещё раз</ApButton>
    </section>
  )
}

function recoveryHint(reason: PhotoRecoveryStep['reason']): string {
  if (reason === 'provider_error') return 'Сервис проверки временно недоступен. Состояние задачи и снимок уже сохранены.'
  if (reason === 'wrong_photo') return 'Сверь условие на экране и сними страницу с решением именно этой задачи.'
  if (reason === 'unreadable') return 'Положи лист ровно, включи свет и оставь в кадре все вычисления.'
  return 'Сними всю страницу сверху, чтобы были видны условие, вычисления и ответ.'
}

function formatFileSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
    : `${Math.max(1, Math.round(bytes / 1024))} КБ`
}

function CameraIcon() {
  return <svg className="button-icon" viewBox="0 0 24 24" aria-hidden><path d="M8.5 5.5 10 3.8h4l1.5 1.7H19a2 2 0 0 1 2 2v9.2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7.5a2 2 0 0 1 2-2h3.5Z"/><circle cx="12" cy="12" r="3.5"/></svg>
}

function ArrowIcon() {
  return <svg className="button-icon" viewBox="0 0 24 24" aria-hidden><path d="M5 12h14m-5-5 5 5-5 5"/></svg>
}

function CheckIcon() {
  return <svg className="button-icon" viewBox="0 0 24 24" aria-hidden><path d="m5 12 4 4L19 6"/></svg>
}

function InfoIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.01"/></svg>
}

function SparkIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden><path d="M12 2c.8 5.2 3.3 7.7 8.5 8.5-5.2.8-7.7 3.3-8.5 8.5-.8-5.2-3.3-7.7-8.5-8.5C8.7 9.7 11.2 7.2 12 2Z"/></svg>
}

function PencilIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden><path d="m4 16-.8 4.8L8 20l10.8-10.8-4-4L4 16Z"/><path d="m13.8 6.2 4 4"/></svg>
}

function ShieldIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden><path d="M12 3 5 6v5c0 4.5 2.7 7.8 7 10 4.3-2.2 7-5.5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></svg>
}

function RefreshIcon() {
  return <svg className="button-icon" viewBox="0 0 24 24" aria-hidden><path d="M20 11a8 8 0 1 0-2.3 5.7L20 14"/><path d="M20 7v4h-4"/></svg>
}
