import { describe, it, expect } from 'vitest'
import { createLadder, normalizeAnswer, answersMatch } from '../lib/ladder'
import type { StepDTO } from '../lib/types'

const STEPS: StepDTO[] = [
  {
    n: 1,
    instruction_ru: 'Сколько будет 2 + 3?',
    micro_skill: 'addition',
    micro_skill_label: 'Сложение',
    kind: 'compute',
    reveal: 'Сложи два числа.',
  },
  {
    n: 2,
    instruction_ru: 'Сколько будет 4 × 3?',
    micro_skill: 'multiplication',
    micro_skill_label: 'Умножение',
    kind: 'compute',
    reveal: null,
  },
  {
    n: 3,
    instruction_ru: 'Сколько будет 10 - 7?',
    micro_skill: 'subtraction',
    micro_skill_label: 'Вычитание',
    kind: 'compute',
    reveal: null,
  },
]

describe('normalizeAnswer', () => {
  it('убирает пробелы и нормализует запятую', () => {
    expect(normalizeAnswer('  0,5  ')).toBe('0.5')
  })

  it('сокращает дробь', () => {
    expect(normalizeAnswer('2/4')).toBe('1/2')
  })

  it('оставляет целое как есть', () => {
    expect(normalizeAnswer('42')).toBe('42')
  })
})

describe('answersMatch', () => {
  it('сравнивает эквивалентные формы без участия UI-флоу', () => {
    expect(answersMatch('1/2', '0.5')).toBe(true)
    expect(answersMatch('0,5', '1/2')).toBe(true)
    expect(answersMatch('3', '4')).toBe(false)
    expect(answersMatch('', '5')).toBe(false)
  })
})

describe('createLadder — применяет серверный verdict', () => {
  it('correct переводит к следующему canonical-шагу', () => {
    const ladder = createLadder(STEPS)
    expect(ladder.activeRung?.stepN).toBe(1)

    expect(ladder.resolve(true, '5')).toBe('correct')
    expect(ladder.activeRung?.stepN).toBe(2)
    expect(ladder.rungs[0]?.submitted_value).toBe('5')
  })

  it('три server-confirmed verdict завершают лесенку', () => {
    const ladder = createLadder(STEPS)
    ladder.resolve(true, '5')
    ladder.resolve(true, '12')
    ladder.resolve(true, '3')

    expect(ladder.activeRung).toBeNull()
    expect(ladder.finished).toBe(true)
  })

  it('wrong остаётся на шаге и включает подсказку', () => {
    const ladder = createLadder(STEPS)

    expect(ladder.resolve(false)).toBe('wrong')
    expect(ladder.activeRung?.stepN).toBe(1)
    expect(ladder.attempts).toBe(1)
    expect(ladder.hint).toBe(true)
  })

  it('не вставляет локальную mock-задачу после повторной ошибки', () => {
    const ladder = createLadder(STEPS)
    ladder.resolve(false)
    ladder.resolve(false)

    expect(ladder.rungs).toHaveLength(3)
    expect(ladder.activeRung?.stepN).toBe(1)
    expect(ladder.attempts).toBe(2)
  })
})

describe('createLadder — resume из backend', () => {
  it('открывает первый ещё не подтверждённый шаг', () => {
    const ladder = createLadder(STEPS, [1, 2])

    expect(ladder.rungs[0]?.status).toBe('solved')
    expect(ladder.rungs[1]?.status).toBe('solved')
    expect(ladder.activeRung?.stepN).toBe(3)
  })

  it('полностью решённая лесенка восстанавливается завершённой', () => {
    const ladder = createLadder(STEPS, [1, 2, 3])

    expect(ladder.activeRung).toBeNull()
    expect(ladder.finished).toBe(true)
  })
})
