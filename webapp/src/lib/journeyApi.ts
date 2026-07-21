import { clearToken, getToken } from './auth'

const JOURNEY_BASE = '/api/journey'

export type JourneyStage =
  | 'profile'
  | 'exam_map'
  | 'diagnostic_intro'
  | 'diagnostic_question'
  | 'diagnostic_result'
  | 'route_ready'
  | 'lesson_intro'
  | 'independent_task'
  | 'guided_step'
  | 'transfer_task'
  | 'typed_processing'
  | 'guided_processing'
  | 'photo_processing'
  | 'photo_feedback'
  | 'photo_recovery'
  | 'transfer_feedback'
  | 'topic_result'
  | 'route_complete'

export interface ExamBlock {
  name: string
  questions: number
  minutes: number
  covered: boolean
}

export interface ExamMap {
  title: string
  scope_note: string
  cycle?: string
  verified_on?: string
  source_url?: string
  source_note?: string
  disclaimer?: string
  day_one: ExamBlock[]
}

export type TargetWindow = 'spring-2027' | 'later'
export type PrepExperience = 'new' | 'self' | 'teacher'
export type MockMathBand = 'not-taken' | '0-20' | '21-30' | '31-40'

export interface JourneyProfile {
  target: 'nis-grade-7'
  weekly_goal: number
  session_minutes: 20 | 30 | 45
  target_window: TargetWindow
  prep_experience: PrepExperience
  weak_topics: string[]
  strong_topics: string[]
  mock_math_band: MockMathBand
  language: 'ru'
}

export type JourneyProfileInput = Omit<JourneyProfile, 'target' | 'language'>

export interface JourneyTopic {
  id: string
  title: string
  strand: string
  goal: string
  reason: string
  status: 'next' | 'planned' | 'completed'
  diagnostic_level?: DiagnosticSkillLevel
}

export type DiagnosticSkillLevel = 'foundation' | 'developing' | 'secure' | 'unmeasured'

export interface DiagnosticSkill {
  id: string
  title: string
  level: DiagnosticSkillLevel
  label: string
  route_topic_id: string | null
}

export interface JourneyRoute {
  topics: JourneyTopic[]
  index: number
  completed: string[]
  skill_profile?: DiagnosticSkill[]
}

export interface JourneyProblem {
  id: number
  content_idx: number | null
  node_id: string
  statement: string
  topic: { id: string; title: string }
}

interface PrimaryStep {
  type: JourneyStage
  title: string
  primary_action: string
}

export interface ProfileStep extends PrimaryStep {
  type: 'profile'
  student: { name: string; grade: number | null }
  description: string
  screen: 0 | 1 | 2 | 3
  substep: 0 | 1 | 2
  screen_count: 4
  draft: JourneyProfile
}

export interface ExamMapStep extends PrimaryStep {
  type: 'exam_map'
  scope_note: string
}

export interface DiagnosticIntroStep extends PrimaryStep {
  type: 'diagnostic_intro'
  description: string
  estimated_minutes: number
}

export interface DiagnosticQuestionStep extends PrimaryStep {
  type: 'diagnostic_question'
  progress: { answered: number; current: number; planned: number }
  question: { id: number; statement: string; answer_type: string }
}

export interface DiagnosticResultStep extends PrimaryStep {
  type: 'diagnostic_result'
  score: { correct: number; total: number }
  skill_profile: DiagnosticSkill[]
  description: string
}

export interface RouteReadyStep extends PrimaryStep {
  type: 'route_ready'
  topics: JourneyTopic[]
}

export interface LessonIntroStep extends PrimaryStep {
  type: 'lesson_intro'
  topic: JourneyTopic
  description: string
  goal: string
}

export interface JourneyTypedFeedback {
  verdict: 'correct' | 'incorrect' | 'unsure'
  message: string
  error_focus: 'none' | 'interpretation' | 'calculation' | 'units' | 'format' | 'unknown'
  counts_for_mastery: boolean
}

export interface PhotoTaskStep extends PrimaryStep {
  type: 'independent_task' | 'transfer_task'
  mode: 'independent' | 'transfer'
  problem: JourneyProblem
  instruction: string
  photo_required: boolean
  help_available: boolean
  photo_consent_required: boolean
  typed_feedback?: JourneyTypedFeedback
  preserved_answer?: { value: string }
}

export interface PhotoProcessingStep extends PrimaryStep {
  type: 'photo_processing'
  problem: JourneyProblem
  message: string
  preserved_photo: { name: string }
}

export interface TypedProcessingStep extends PrimaryStep {
  type: 'typed_processing'
  problem: JourneyProblem
  message: string
  preserved_answer: { value: string }
}

export interface GuidedStep extends PrimaryStep {
  type: 'guided_step'
  problem: JourneyProblem
  step: GuidedStepPrompt
  feedback: GuidedStepFeedback | null
  photo_required: false
  mastery_note: string
}

export interface GuidedStepPrompt {
  number: number
  total: number
  instruction: string
  prompt: string
  format_hint: string
  example: string
  input_mode: 'decimal' | 'text'
}

export interface GuidedStepFeedback {
  verdict: 'correct' | 'incorrect' | 'unsure'
  message: string
  answer?: string
  completed_step_n?: number
  reason?: 'provider_error'
}

export interface GuidedProcessingStep extends PrimaryStep {
  type: 'guided_processing'
  problem: JourneyProblem
  step: GuidedStepPrompt
  message: string
  preserved_answer: { value: string }
}

export interface JourneyMastery {
  value: number
  threshold: number
  reached: boolean
  evidence?: {
    correct: number
    required_correct: number
    remaining_correct: number
    total: number
    accuracy: number | null
    minimum_accuracy: number
    probability_reached: boolean
    correct_reached: boolean
    accuracy_reached: boolean
  }
}

export interface PhotoFeedbackStep {
  type: 'photo_feedback' | 'transfer_feedback'
  problem: JourneyProblem
  verdict: 'correct' | 'incorrect'
  message: string
  failed_step?: number
  confirmed_steps?: Array<{ number: number; label: string }>
  correction?: string
  help_available?: boolean
  mastery?: JourneyMastery
  primary_action: string
}

export interface PhotoRecoveryStep {
  type: 'photo_recovery'
  problem: JourneyProblem
  reason: 'unreadable' | 'wrong_photo' | 'unsure' | 'provider_error'
  message: string
  preserved_photo: { name: string }
  return_stage: 'independent_task' | 'transfer_task'
  primary_action: string
}

export interface TopicResultStep extends PrimaryStep {
  type: 'topic_result'
  topic: JourneyTopic
  mastery: JourneyMastery
}

export interface RouteCompleteStep extends PrimaryStep {
  type: 'route_complete'
  description: string
}

export type JourneyNextStep =
  | ProfileStep
  | ExamMapStep
  | DiagnosticIntroStep
  | DiagnosticQuestionStep
  | DiagnosticResultStep
  | RouteReadyStep
  | LessonIntroStep
  | PhotoTaskStep
  | TypedProcessingStep
  | GuidedProcessingStep
  | PhotoProcessingStep
  | GuidedStep
  | PhotoFeedbackStep
  | PhotoRecoveryStep
  | TopicResultStep
  | RouteCompleteStep

export type JourneyWorkspaceMode = 'independent' | 'transfer'
export type JourneyEvidenceStatus = 'empty' | 'processing' | 'checked' | 'preserved' | 'guided'
export type JourneyWorkspaceVerdict = 'correct' | 'needs_revision' | 'uncertain'
export type JourneyRecoveryReason =
  | 'unreadable'
  | 'wrong_photo'
  | 'unsure'
  | 'provider_error'
  | 'unknown'
export type JourneyContextLayerKind = 'closed' | 'processing' | 'feedback' | 'uncertain' | 'guided'

export interface JourneyWorkspaceTask {
  journey_id: number
  problem_id: number
  topic: { id: string; title: string }
  mode: JourneyWorkspaceMode
  statement: string
  position: number
}

export interface JourneyLearnerEvidence {
  kind: 'photo' | 'typed'
  status: JourneyEvidenceStatus
  label: string | null
}

export interface JourneyContextLayer {
  kind: JourneyContextLayerKind
  verdict: JourneyWorkspaceVerdict | null
  recovery_reason: JourneyRecoveryReason | null
}

export interface JourneyWorkspaceResponse {
  default_mode: 'photo' | 'typed'
  typed_available: boolean
  help_available: boolean
}

export interface JourneyWorkspaceSupport {
  used: boolean
  highest_hint_rung: number
}

export interface JourneyWorkspaceEnvelope {
  workspace_version: 1
  task: JourneyWorkspaceTask
  learner_evidence: JourneyLearnerEvidence
  context_layer: JourneyContextLayer
  response: JourneyWorkspaceResponse
  support: JourneyWorkspaceSupport
}

export type JourneyState = {
  journey_id: number
  revision: number
  next_step: JourneyNextStep
  context: { exam_map: ExamMap; profile?: JourneyProfile; route: JourneyRoute }
} & Partial<JourneyWorkspaceEnvelope>

export type ActiveJourneyState = JourneyState & JourneyWorkspaceEnvelope

export function hasJourneyWorkspace(state: JourneyState): state is ActiveJourneyState {
  const { task, learner_evidence: evidence, context_layer: layer, response, support } = state
  return state.workspace_version === 1
    && task?.journey_id === state.journey_id
    && Number.isInteger(task.problem_id)
    && typeof task.statement === 'string'
    && task.statement.length > 0
    && Number.isInteger(task.position)
    && task.position > 0
    && (evidence?.kind === 'photo' || evidence?.kind === 'typed')
    && layer !== undefined
    && (response?.default_mode === 'photo' || response?.default_mode === 'typed')
    && typeof response.typed_available === 'boolean'
    && typeof response.help_available === 'boolean'
    && support !== undefined
    && typeof support.used === 'boolean'
    && Number.isInteger(support.highest_hint_rung)
}

interface ErrorDetail {
  code?: string
  message?: string
  state?: JourneyState
}

export class JourneyApiError extends Error {
  status: number
  code: string
  state: JourneyState | null

  constructor(status: number, message: string, code = 'request_failed', state: JourneyState | null = null) {
    super(message)
    this.name = 'JourneyApiError'
    this.status = status
    this.code = code
    this.state = state
  }
}

function headers(json = false): HeadersInit {
  const token = getToken()
  return {
    Accept: 'application/json',
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function journeyRequest(path: string, init?: RequestInit): Promise<JourneyState> {
  let response: Response
  try {
    response = await fetch(`${JOURNEY_BASE}${path}`, init)
  } catch {
    throw new JourneyApiError(
      0,
      navigator.onLine
        ? 'Не получилось связаться с сервером. Попробуй ещё раз.'
        : 'Нет соединения. Ответ или выбранное фото останутся на этом экране.',
      'offline',
    )
  }

  if (!response.ok) {
    let payload: { detail?: string | ErrorDetail } | null = null
    try {
      payload = await response.json() as { detail?: string | ErrorDetail }
    } catch {
      // Статус остаётся источником истины, даже если reverse proxy вернул HTML.
    }
    const detail = payload?.detail
    const structured = typeof detail === 'object' && detail !== null ? detail : null
    if (response.status === 401) clearToken()
    throw new JourneyApiError(
      response.status,
      typeof detail === 'string'
        ? detail
        : structured?.message ?? 'Не удалось выполнить действие. Попробуй ещё раз.',
      structured?.code ?? `http_${response.status}`,
      structured?.state ?? null,
    )
  }

  return response.json() as Promise<JourneyState>
}

function postJson(path: string, body: object): Promise<JourneyState> {
  return journeyRequest(path, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify(body),
  })
}

export function fetchJourney(): Promise<JourneyState> {
  return journeyRequest('/current', { headers: headers() })
}

export function saveJourneyProfile(body: JourneyProfile & { revision: number }): Promise<JourneyState> {
  return postJson('/profile', body)
}

export function saveJourneyProfileDraft(body: JourneyProfile & {
  revision: number
  screen: 0 | 1 | 2 | 3
  substep: 0 | 1 | 2
}): Promise<JourneyState> {
  return postJson('/profile/draft', body)
}

export function continueJourney(body: { revision: number; action: string }): Promise<JourneyState> {
  return postJson('/continue', body)
}

export function submitDiagnosticAnswer(body: {
  revision: number
  question_id: number
  answer: string
  client_attempt_id: string
}): Promise<JourneyState> {
  return postJson('/diagnostic/answer', body)
}

export function requestJourneyHelp(body: { revision: number; problem_id: number }): Promise<JourneyState> {
  return postJson('/help', body)
}

export function submitGuidedAnswer(body: {
  revision: number
  problem_id: number
  step_n: number
  answer: string
  client_attempt_id: string
}): Promise<JourneyState> {
  return postJson('/guided/answer', body)
}

export function submitTypedAnswer(body: {
  revision: number
  problem_id: number
  answer: string
  client_attempt_id: string
}): Promise<JourneyState> {
  return postJson('/answer', body)
}

export function uploadJourneyPhoto(body: {
  revision: number
  problem_id: number
  client_attempt_id: string
  photo: File
}): Promise<JourneyState> {
  const form = new FormData()
  form.set('revision', String(body.revision))
  form.set('problem_id', String(body.problem_id))
  form.set('client_attempt_id', body.client_attempt_id)
  form.set('photo', body.photo)
  return journeyRequest('/photo', {
    method: 'POST',
    headers: headers(),
    body: form,
  })
}

export function retryJourneyPhoto(body: { revision: number }): Promise<JourneyState> {
  return postJson('/photo/retry', body)
}
