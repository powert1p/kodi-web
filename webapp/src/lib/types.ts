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
  expected_value: string
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
  /** Правильный ответ. */
  answer: string
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
