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
  decomp_idx: number | null
  steps: StepDTO[]
  state: TaskState
  /** Что ученик ответил в прошлый раз (для эмпатичного «почти»). */
  wrong_answer: string
  /** Текущее владение узлом, 0..1. */
  mastery: number
}

/** Один повторяющийся тип ошибки ученика (для экрана «Прогресс»). */
export interface ErrorType {
  /** Стабильный ключ микро-навыка. */
  micro_skill: string
  /** Человекочитаемый ярлык (ru). */
  label: string
  /** Тема/узел, к которому относится навык. */
  topic_label: string
  /** Сколько раз ошибка повторялась. */
  count: number
  /** Последняя причина — короткая эмпатичная строка (или null). */
  last_cause: string | null
}

/** Аналитика тренажёра: топ повторяющихся ошибок ученика. */
export interface AnalyticsData {
  /** Топ типов ошибок, отсортированы по убыванию count. */
  error_types: ErrorType[]
}

/** Диагноз ошибки (визуальный разбор по фото/тексту решения). */
export interface Diagnosis {
  transcription: string
  /** Номер провального шага; null — определить не удалось. */
  failed_step: number | null
  cause_text: string
  level: number
  micro_skill: string | null
  /** Уверенность диагноза, 0..1. */
  confidence: number
  image_ref: string
}
