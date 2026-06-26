// Чистая (без React) конечная машина состояний лесенки.
// Портировано из cabinet/src/hooks/useLadder.ts + cabinet/src/lib/math.ts.
// Мутирует внутренний state объекта — вызывающий код получает актуальные данные
// через геттеры (rungs, activeRung, attempts, hint, finished).

import type { StepDTO } from './types'

// ——————————————————————————————————
// Математика: нормализация и сравнение ответов
// ——————————————————————————————————

function gcd(a: number, b: number): number {
  a = Math.abs(a)
  b = Math.abs(b)
  while (b) [a, b] = [b, a % b]
  return a || 1
}

/** Нормализует строку-ответ: сокращает дробь, унифицирует разделитель, убирает пробелы. */
export function normalizeAnswer(raw: string): string {
  const t = raw.trim().replace(/\s+/g, '').replace(',', '.')
  const frac = t.match(/^(-?\d+)\/(\d+)$/)
  if (frac) {
    const num = parseInt(frac[1]!, 10)
    const den = parseInt(frac[2]!, 10)
    if (den === 0) return t
    const g = gcd(num, den)
    const sign = den < 0 ? -1 : 1
    return `${(num / g) * sign}/${Math.abs(den / g)}`
  }
  return t
}

/** Сравнивает ответ ученика с эталоном через нормализацию.
 *  Поддерживает дроби (1/2 === 0.5) и запятую как разделитель (0,5 === 0.5). */
export function answersMatch(input: string, expected: string): boolean {
  if (!input.trim()) return false

  // Нормализуем оба
  const normInput = normalizeAnswer(input)
  const normExpected = normalizeAnswer(expected)
  if (normInput === normExpected) return true

  // Кросс-сравнение дробь ↔ десятичная: конвертируем оба в float
  const toFloat = (s: string): number | null => {
    const frac = s.match(/^(-?\d+)\/(\d+)$/)
    if (frac) {
      const num = parseInt(frac[1]!, 10)
      const den = parseInt(frac[2]!, 10)
      return den === 0 ? null : num / den
    }
    const f = parseFloat(s)
    return isNaN(f) ? null : f
  }

  const fi = toFloat(normInput)
  const fe = toFloat(normExpected)
  if (fi !== null && fe !== null) {
    return Math.abs(fi - fe) < 1e-9
  }
  return false
}

// ——————————————————————————————————
// Типы ступеней лесенки
// ——————————————————————————————————

/** Происхождение ступени: оригинальная из задачи или вставленная «попроще». */
export type RungKind = 'original' | 'easier'

/** Статус прохождения ступени. */
export type RungStatus = 'locked' | 'active' | 'solved'

/** Одна ступень лесенки. */
export interface Rung {
  /** Уникальный ключ ступени. */
  key: string
  kind: RungKind
  instruction: string
  microSkill: string
  /** Ожидаемый ответ для сравнения. */
  expected_value: string
  status: RungStatus
  reveal: string | null
  /** Для easier: ключ исходной ступени, к которой возвращаемся после решения. */
  parentKey?: string
}

/** Необязательный параметр «ступень попроще» для climb-down. */
export interface EasierRung {
  instruction: string
  microSkill: string
  expected: string
}

/** Публичное API объекта-лесенки (мутирующее, не иммутабельное). */
export interface LadderState {
  /** Текущий массив ступеней (включая вставленные easier). */
  readonly rungs: readonly Rung[]
  /** Активная ступень или null, если лесенка завершена. */
  readonly activeRung: Rung | null
  /** Количество попыток на текущей ступени. */
  readonly attempts: number
  /** true — показывать подсказку ученику. */
  readonly hint: boolean
  /** true — все ступени решены. */
  readonly finished: boolean
  /** Отправить ответ. Возвращает результат шага. */
  submit(value: string): 'correct' | 'wrong' | 'inserted'
}

// ——————————————————————————————————
// Фабрика лесенки
// ——————————————————————————————————

/**
 * Создаёт объект-лесенку из шагов задачи.
 *
 * @param steps — шаги задачи (StepDTO[]) из API
 * @param easierRung — необязательная ступень «попроще» для climb-down при 2-й ошибке
 * @returns объект LadderState с мутирующим submit()
 */
export function createLadder(steps: StepDTO[], easierRung?: EasierRung): LadderState {
  // Внутренний изменяемый массив ступеней
  let rungs: Rung[] = steps.map((s, i) => ({
    key: `s${s.n}`,
    kind: 'original' as RungKind,
    instruction: s.instruction_ru,
    microSkill: s.micro_skill,
    expected_value: s.expected_value,
    status: (i === 0 ? 'active' : 'locked') as RungStatus,
    reveal: s.reveal,
  }))

  let attempts = 0
  let hint = false

  // Геттер: текущая активная ступень
  const getActiveRung = (): Rung | null =>
    rungs.find((r) => r.status === 'active') ?? null

  const getFinished = (): boolean =>
    rungs.length > 0 && rungs.every((r) => r.status === 'solved')

  const submit = (value: string): 'correct' | 'wrong' | 'inserted' => {
    const activeIdx = rungs.findIndex((r) => r.status === 'active')
    if (activeIdx === -1) return 'wrong'

    const active = rungs[activeIdx]!

    // Проверяем ответ
    if (answersMatch(value, active.expected_value)) {
      // Верно: помечаем решённой
      rungs[activeIdx] = { ...active, status: 'solved' }

      // Если это была easier-ступень — активируем её parent (climb back)
      if (active.kind === 'easier' && active.parentKey) {
        const parentIdx = rungs.findIndex((r) => r.key === active.parentKey)
        if (parentIdx !== -1) {
          rungs[parentIdx] = { ...rungs[parentIdx]!, status: 'active' }
        }
      } else {
        // Активируем следующую locked-ступень
        const nextIdx = rungs.findIndex((r) => r.status === 'locked')
        if (nextIdx !== -1) {
          rungs[nextIdx] = { ...rungs[nextIdx]!, status: 'active' }
        }
      }

      attempts = 0
      hint = false
      return 'correct'
    }

    // Неверно: увеличиваем счётчик
    attempts += 1
    hint = true

    // 2-я ошибка на оригинальной ступени → climb-down (если easier есть и ещё не давалась)
    const alreadyHasEasier = rungs.some((r) => r.parentKey === active.key)
    if (attempts >= 2 && active.kind === 'original' && !alreadyHasEasier && easierRung) {
      const insertedRung: Rung = {
        key: `${active.key}-easy`,
        kind: 'easier',
        instruction: easierRung.instruction,
        microSkill: easierRung.microSkill,
        expected_value: easierRung.expected,
        status: 'active',
        reveal: null,
        parentKey: active.key,
      }

      // Оригинальную ступень → locked; вставляем easier ПЕРЕД ней
      rungs[activeIdx] = { ...active, status: 'locked' }
      rungs.splice(activeIdx, 0, insertedRung)

      attempts = 0
      hint = false
      return 'inserted'
    }

    return 'wrong'
  }

  // Возвращаем объект с геттерами — актуальные данные по ссылке на замыкание
  return {
    get rungs() { return rungs as readonly Rung[] },
    get activeRung() { return getActiveRung() },
    get attempts() { return attempts },
    get hint() { return hint },
    get finished() { return getFinished() },
    submit,
  }
}
