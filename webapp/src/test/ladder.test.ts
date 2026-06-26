import { describe, it, expect } from 'vitest'
import { createLadder, normalizeAnswer, answersMatch } from '../lib/ladder'
import type { StepDTO } from '../lib/types'

// Фикстура: три ступени лесенки для золотых последовательностей.
const STEPS: StepDTO[] = [
  {
    n: 1,
    instruction_ru: 'Сколько будет 2 + 3?',
    micro_skill: 'addition',
    expected_value: '5',
    kind: 'compute',
    reveal: 'Просто сложи: 2 + 3 = 5',
  },
  {
    n: 2,
    instruction_ru: 'Сколько будет 4 × 3?',
    micro_skill: 'multiplication',
    expected_value: '12',
    kind: 'compute',
    reveal: null,
  },
  {
    n: 3,
    instruction_ru: 'Сколько будет 10 - 7?',
    micro_skill: 'subtraction',
    expected_value: '3',
    kind: 'compute',
    reveal: null,
  },
]

const EASIER_RUNG = {
  instruction: 'Сколько будет 1 + 1?',
  microSkill: 'addition',
  expected: '2',
}

// ——————————————————————————————————
// Нормализация и сравнение ответов
// ——————————————————————————————————

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
  it('1/2 === 0.5 → true', () => {
    expect(answersMatch('1/2', '0.5')).toBe(true)
  })

  it('3 !== 4 → false', () => {
    expect(answersMatch('3', '4')).toBe(false)
  })

  it('0,5 === 1/2 → true (запятая как разделитель)', () => {
    expect(answersMatch('0,5', '1/2')).toBe(true)
  })

  it('пустой ввод → false', () => {
    expect(answersMatch('', '5')).toBe(false)
  })
})

// ——————————————————————————————————
// Золотые последовательности createLadder
// ——————————————————————————————————

describe('createLadder — correct advances', () => {
  it('верный ответ на первой ступени переводит к второй', () => {
    const ladder = createLadder(STEPS)
    const result = ladder.submit('5')
    expect(result).toBe('correct')
    expect(ladder.activeRung?.expected_value).toBe('12')
  })

  it('три верных ответа подряд завершают лесенку', () => {
    const ladder = createLadder(STEPS)
    ladder.submit('5')
    ladder.submit('12')
    ladder.submit('3')
    expect(ladder.activeRung).toBeNull()
    expect(ladder.finished).toBe(true)
  })
})

describe('createLadder — 1st wrong shows hint', () => {
  it('первая ошибка: returns "wrong", attempts=1, hint=true', () => {
    const ladder = createLadder(STEPS)
    const result = ladder.submit('99')
    expect(result).toBe('wrong')
    expect(ladder.attempts).toBe(1)
    expect(ladder.hint).toBe(true)
  })
})

describe('createLadder — 2nd wrong on original inserts exactly ONE easier rung', () => {
  it('вставляет easier перед оригинальной и сбрасывает attempts', () => {
    const ladder = createLadder(STEPS, EASIER_RUNG)
    ladder.submit('99') // 1-я ошибка
    const result = ladder.submit('99') // 2-я ошибка
    expect(result).toBe('inserted')
    // Easier должна быть активной
    expect(ladder.activeRung?.expected_value).toBe('2')
    // attempts сбрасываются после вставки
    expect(ladder.attempts).toBe(0)
    // Всего ступеней теперь 4 (1 easier + 3 original)
    expect(ladder.rungs.length).toBe(4)
  })

  it('вставляет easier РОВНО ОДИН раз, повторный submit=wrong без второй вставки', () => {
    const ladder = createLadder(STEPS, EASIER_RUNG)
    ladder.submit('99')
    ladder.submit('99') // вставляет easier, теперь active = easier
    // Ошибаемся на easier: не должна вставлять ещё одну
    ladder.submit('99') // 1-я ошибка на easier
    const result = ladder.submit('99') // 2-я ошибка на easier (kind=easier → no insert)
    expect(result).toBe('wrong')
    // Количество ступеней не увеличилось
    expect(ladder.rungs.length).toBe(4)
  })
})

describe('createLadder — 2nd wrong without easierRung → reveal path (wrong)', () => {
  it('без easier второй неверный ответ возвращает "wrong" (не "inserted")', () => {
    const ladder = createLadder(STEPS) // без easierRung
    ladder.submit('99')
    const result = ladder.submit('99')
    expect(result).toBe('wrong')
    expect(ladder.rungs.length).toBe(3)
  })
})

describe('createLadder — climb back after easier', () => {
  it('верный ответ на easier возвращает к исходной оригинальной', () => {
    const ladder = createLadder(STEPS, EASIER_RUNG)
    ladder.submit('99')
    ladder.submit('99') // вставили easier (active=easier "2")
    ladder.submit('2')  // верно на easier → climb back к "5"
    expect(ladder.activeRung?.expected_value).toBe('5')
  })
})
