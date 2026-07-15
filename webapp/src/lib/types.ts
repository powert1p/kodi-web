// Зеркало backend-JSON «Работа над ошибками». Источник правды для всех фич.
// Меняешь форму ответа на бэке — правишь здесь и сверяешь Pydantic-схемы.

/** Состояние разбора задачи (светофор). */
export type TaskState = 'revisit' | 'almost' | 'got'

/** Тип шага лесенки: вычислить значение или выбрать вариант. */
export type StepKind = 'compute' | 'choose'

/** Один шаг разбора (rung лесенки). */
export interface StepDTO {
  n: number
  instruction_ru: string
  micro_skill: string
  /** Человеческая подпись micro_skill (label_ru); null — код не найден в каталоге.
   * Показывать пользователю ТОЛЬКО её, никогда — micro_skill (запрет DESIGN_SYSTEM §2.2). */
  micro_skill_label: string | null
  kind: StepKind
  /** Подсказка-раскрытие; null — раскрытия нет. */
  reveal: string | null
}

/** Задача, в которой ученик ошибся, с разбором по шагам. */
export interface WrongTask {
  id: string
  problem_id: number
  node_id: string
  topic_label: string
  /** Условие задачи; может содержать инлайн-LaTeX в $...$. */
  statement: string
  primary_micro_skill: string | null
  /** Человеческая подпись primary_micro_skill (label_ru); см. запрет §2.2. */
  primary_micro_skill_label: string | null
  decomp_idx: number | null
  steps: StepDTO[]
  state: TaskState
  /** Что ученик ответил в прошлый раз (для эмпатичного «почти»). */
  wrong_answer: string
  /** Текущее владение узлом, 0..1. */
  mastery: number
  /** Карточка метода узла «Как решать» (Метод/Пример/Ловушка); null — ещё не сгенерирована. */
  theory_ru: string | null
}

/** Запись повторяющейся ошибки ученика (зеркало BE RecurringErrorOut). */
export interface RecurringErrorOut {
  micro_skill: string
  label_ru: string | null
  error_count: number
  last_cause_text: string | null
  node_id: string | null
}

/** Глобальный топ ошибок (только для владельца). */
export interface GlobalErrorOut {
  micro_skill: string
  label_ru: string | null
  total_errors: number
  students_affected: number
}

/** Аналитика тренажёра (зеркало BE AnalyticsResponse). */
export interface AnalyticsData {
  my_top: RecurringErrorOut[]
  global_top?: GlobalErrorOut[]
}

/** View-модель строки аналитики (не BE-контракт; строится из RecurringErrorOut). */
export interface ErrorType {
  micro_skill: string
  label: string
  topic_label: string
  count: number
  last_cause: string | null
}

/** Проблемная тема ученика (зеркало BE ProblemTopicOut). */
export interface ProblemTopic {
  topic_id: string
  strand: string | null
  name_ru: string | null
  error_count: number
  top_micro_skills: string[]
  nodes_mastery_avg: number
  closure_progress: number
}

/** Одна реплика чата тьютора. */
export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Ответ POST /tutor/chat. */
export interface TutorChatResponse {
  session_id: number
  reply: string
  history: TutorMessage[]
}

/** Контрольная задача из BE verification/start. */
export interface VerificationProblemDTO {
  problem_id: number
  node_id: string
  topic_label: string
  statement: string
  micro_skill: string | null
  /** Человеческая подпись micro_skill (label_ru); см. запрет §2.2. */
  micro_skill_label: string | null
  xp: number
}

/** Одна задача мини-среза (Блок 1.0). Правильный ответ на клиент НЕ приходит. */
export interface SrezTask {
  problem_id: number
  statement: string
  answer_type: string | null
  node_title: string
  position: number
  total: number
}

/** Тип вердикта проверки одного шага лесенки (Блок 1.2). */
export type StepVerdictKind = 'match' | 'mismatch' | 'unsure'

/** Вердикт проверки шага (зеркало BE StepSubmitOut). */
export interface StepVerdict {
  verdict: StepVerdictKind
  /** Подсказка при mismatch (fingerprint-hint); null — раскрытия нет. */
  hint: string | null
  confidence: number
  step_n: number
}

/** Серверный вердикт typed-answer; эталон ответа намеренно отсутствует. */
export interface StepAnswerVerdict {
  correct: boolean
  hint: string | null
  step_n: number
}

/** Восстановимый прогресс лесенки, подтверждённый backend. */
export interface DrillState {
  solved_step_ns: number[]
}

/** Диагноз ошибки (визуальный разбор по фото/тексту решения). */
export interface Diagnosis {
  transcription: string
  /** Номер провального шага; null — определить не удалось. */
  failed_step: number | null
  cause_text: string
  level: number
  micro_skill: string | null
  /** Человеческая подпись micro_skill (label_ru); см. запрет §2.2. */
  micro_skill_label: string | null
  /** Уверенность диагноза, 0..1. */
  confidence: number
  image_ref: string
}

// ── Учебный путь ──

export type LearningRole = 'worked' | 'guided' | 'independent' | 'transfer'
export type LearningStatus = 'active' | 'completed'
export type LearningLessonStatus = 'not_started' | LearningStatus

export interface LearningLessonSummary {
  id: string
  title: string
  lesson_title: string
  goal: string
  result_label: string
  duration_minutes: number
}

export interface LearningPathLesson extends LearningLessonSummary {
  status: LearningLessonStatus
  progress: { completed: number; total: number; current_role: LearningRole | null }
  primary_action: { label: string; lesson_id: string }
}

export interface LearningPathSummary {
  id: string
  title: string
  current_block: {
    id: string
    title: string
    completed_lessons: number
    total_lessons: number
  }
}

export interface LearningPathResponse {
  path: LearningPathSummary
  lesson: LearningPathLesson | null
}

export interface LearningWorkedStep {
  label: string
  expression: string
  result: string
}

/** Student-safe activity: expected answer and future hints never enter this type. */
export interface LearningActivity {
  id: string
  role: LearningRole
  phase_label: string
  title: string
  prompt: string
  statement: string
  answer_type: string | null
  input_suffix: string | null
  embedded_supports: string[]
  worked_steps: LearningWorkedStep[]
  support_level: number
  support: string | null
  last_answer: string | null
}

export interface LearningFeedback {
  is_correct: boolean
  message: string
  is_duplicate: boolean
}

export interface LearningResult {
  title: string
  skill: string
  independent_completed: number
  transfer_completed: number
  without_support: number
  evidence_label: string
}

export interface LearningSessionState {
  session_id: number
  status: LearningStatus
  lesson: LearningLessonSummary
  progress: { current: number; total: number; completed: number }
  activity: LearningActivity | null
  feedback: LearningFeedback | null
  result: LearningResult | null
}
