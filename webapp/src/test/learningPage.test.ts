import { createElement } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LearningPathView } from '../features/learning/LearningPathPage'
import { LearningActivityView } from '../features/learning/LearningActivity'
import { LearningPhaseRail } from '../features/learning/LearningPhaseRail'
import { LearningResultView } from '../features/learning/LearningResult'
import type { LearningActivity, LearningPathLesson, LearningPathSummary, LearningResult } from '../lib/types'

const PATH: LearningPathSummary = {
  id: 'nish-preparation',
  title: 'Подготовка к НИШ',
  current_block: {
    id: 'PC06',
    title: 'Смеси и концентрации',
    completed_lessons: 0,
    total_lessons: 1,
  },
}

const LESSON: LearningPathLesson = {
  id: 'mixtures-1',
  title: 'Смеси и концентрации',
  lesson_title: 'Вещество остаётся',
  goal: 'Пересчитывать концентрацию, когда воду добавили или выпарили.',
  result_label: 'Ты сохраняешь массу вещества.',
  duration_minutes: 12,
  status: 'not_started',
  progress: { completed: 0, total: 6, current_role: 'worked' },
  primary_action: { label: 'Начать урок', lesson_id: 'mixtures-1' },
}

const GUIDED: LearningActivity = {
  id: 'guided-substance',
  role: 'guided',
  phase_label: 'Решаем вместе',
  title: 'Сначала найди неизменную часть',
  prompt: 'Сколько граммов соли было в исходном растворе?',
  statement: 'К 200 г 10%-го раствора добавили 50 г воды.',
  answer_type: 'number',
  input_suffix: 'г',
  embedded_supports: ['Было 200 г раствора.', 'Концентрация — 10%.'],
  worked_steps: [],
  support_level: 1,
  support: 'Начни с 10% от исходных 200 г.',
  last_answer: '40',
}

describe('learning product UI', () => {
  it('показывает текущий блок пути и одну primary action без дневной очереди', () => {
    render(createElement(MemoryRouter, null, createElement(LearningPathView, { path: PATH, lesson: LESSON })))

    expect(screen.getByRole('heading', { name: 'Вещество остаётся' })).toBeTruthy()
    expect(screen.getByText('Мой путь')).toBeTruthy()
    expect(screen.getByText('Текущий блок · Смеси и концентрации')).toBeTruthy()
    expect(screen.getByText('В этом блоке: 0 из 1 урока')).toBeTruthy()
    expect(document.body.textContent).not.toContain('Сегодня')
    expect(screen.getAllByRole('button', { name: 'Начать урок' })).toHaveLength(1)
    for (const forbidden of ['Фото', 'Чат', 'Теория', 'Помощник']) {
      expect(screen.queryByText(forbidden, { exact: true })).toBeNull()
    }
    expect(screen.getAllByRole('listitem')).toHaveLength(4)
  })

  it('путь оставляет guided-фазу активной на всех трёх её activity', () => {
    const guidedLesson: LearningPathLesson = {
      ...LESSON,
      status: 'active',
      progress: { completed: 2, total: 6, current_role: 'guided' },
      primary_action: { label: 'Продолжить', lesson_id: 'mixtures-1' },
    }
    render(createElement(MemoryRouter, null, createElement(LearningPathView, { path: PATH, lesson: guidedLesson })))

    expect(screen.getByText('Доделать').closest('li')?.getAttribute('aria-current')).toBe('step')
    expect(screen.getByText('Решить').closest('li')?.getAttribute('aria-current')).toBeNull()
  })

  it('показывает только текущую серверную подсказку и сохраняет ошибочный ввод', () => {
    const onAnswerChange = vi.fn()
    render(createElement(LearningActivityView, {
      activity: GUIDED,
      answer: '40',
      onAnswerChange,
      onSubmit: vi.fn(),
      onAdvance: vi.fn(),
      isSubmitting: false,
      isAdvancing: false,
      answerError: null,
      advanceError: null,
    }))

    const input = screen.getByRole('textbox', { name: /ответ/i }) as HTMLInputElement
    expect(input.value).toBe('40')
    expect(screen.getByRole('status').textContent).toContain('Начни с 10%')
    expect(screen.queryByText(/раздели 200/i)).toBeNull()
    fireEvent.change(input, { target: { value: '20' } })
    expect(onAnswerChange).toHaveBeenCalledWith('20')
  })

  it('делает четыре фазы постоянными и отмечает текущую', () => {
    render(createElement(LearningPhaseRail, { role: 'independent', completed: false }))

    expect(screen.getAllByRole('listitem')).toHaveLength(4)
    expect(screen.getByText('Сам').getAttribute('aria-current')).toBe('step')
  })

  it('результат показывает реальное evidence без очков и конфетти', () => {
    const result: LearningResult = {
      title: 'Теперь ты умеешь',
      skill: 'Сохранять массу вещества и пересчитывать концентрацию.',
      independent_completed: 2,
      transfer_completed: 1,
      without_support: 1,
      evidence_label: '2 самостоятельных задания, одно — с переносом на новую ситуацию',
    }
    render(createElement(MemoryRouter, null, createElement(LearningResultView, { result })))

    expect(screen.getByText(result.evidence_label)).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
    expect(screen.getByText('1 из 2')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/xp|очки|конфетти/i)
  })
})
