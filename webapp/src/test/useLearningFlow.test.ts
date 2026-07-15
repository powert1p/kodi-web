import { createElement, type ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({
  startLearningLesson: vi.fn(),
  advanceLearningLesson: vi.fn(),
  answerLearningActivity: vi.fn(),
  learningIdentity: vi.fn(() => 'student-1'),
}))

import {
  advanceLearningLesson,
  answerLearningActivity,
  startLearningLesson,
} from '../lib/api'
import { useLearningFlow } from '../features/learning/useLearningFlow'
import type { LearningSessionState } from '../lib/types'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return createElement(QueryClientProvider, { client }, children)
}

const BASE: LearningSessionState = {
  session_id: 10,
  status: 'active',
  lesson: {
    id: 'mixtures-1',
    title: 'Смеси и концентрации',
    lesson_title: 'Вещество остаётся',
    goal: 'Пересчитывать концентрацию',
    result_label: 'Сохраняешь массу вещества',
    duration_minutes: 12,
  },
  progress: { current: 2, total: 6, completed: 1 },
  activity: {
    id: 'guided-substance',
    role: 'guided',
    phase_label: 'Решаем вместе',
    title: 'Сначала найди неизменную часть',
    prompt: 'Сколько граммов соли было?',
    statement: 'К 200 г 10%-го раствора добавили воду.',
    answer_type: 'number',
    input_suffix: 'г',
    embedded_supports: ['Было 200 г раствора.'],
    worked_steps: [],
    support_level: 1,
    support: 'Начни с 10% от 200 г.',
    last_answer: '40',
  },
  feedback: null,
  result: null,
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(startLearningLesson).mockResolvedValue(BASE)
  vi.mocked(advanceLearningLesson).mockResolvedValue(BASE)
})

describe('useLearningFlow', () => {
  it('восстанавливает точный ответ и support после reload', async () => {
    const { result } = renderHook(() => useLearningFlow('mixtures-1'), { wrapper })

    await waitFor(() => expect(result.current.state?.activity?.id).toBe('guided-substance'))
    expect(result.current.answer).toBe('40')
    expect(result.current.state?.activity?.support_level).toBe(1)
  })

  it('при сетевой ошибке сохраняет ввод и повторяет тот же idempotency key', async () => {
    vi.mocked(answerLearningActivity)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({
        ...BASE,
        activity: { ...BASE.activity!, last_answer: '25', support_level: 2 },
        feedback: { is_correct: false, message: 'Пока не сходится.', is_duplicate: false },
      })
    const { result } = renderHook(() => useLearningFlow('mixtures-1'), { wrapper })
    await waitFor(() => expect(result.current.state).not.toBeNull())

    act(() => result.current.changeAnswer('25'))
    act(() => result.current.submitAnswer())
    await waitFor(() => expect(result.current.answerError).toBeTruthy())
    const firstId = vi.mocked(answerLearningActivity).mock.calls[0]?.[0].clientAttemptId
    expect(result.current.answer).toBe('25')

    act(() => result.current.submitAnswer())
    await waitFor(() => expect(answerLearningActivity).toHaveBeenCalledTimes(2))
    const secondId = vi.mocked(answerLearningActivity).mock.calls[1]?.[0].clientAttemptId
    expect(secondId).toBe(firstId)
    expect(result.current.answer).toBe('25')
  })

  it('не отправляет второй ответ, пока первый ещё проверяется', async () => {
    vi.mocked(answerLearningActivity).mockImplementation(() => new Promise(() => undefined))
    const { result } = renderHook(() => useLearningFlow('mixtures-1'), { wrapper })
    await waitFor(() => expect(result.current.state).not.toBeNull())

    act(() => result.current.changeAnswer('20'))
    act(() => {
      result.current.submitAnswer()
      result.current.submitAnswer()
    })

    expect(answerLearningActivity).toHaveBeenCalledTimes(1)
    expect(result.current.isSubmitting).toBe(true)
  })

  it('снимает busy-lock при смене урока во время отправки', async () => {
    vi.mocked(startLearningLesson).mockImplementation(async (lessonId) => ({
      ...BASE,
      lesson: { ...BASE.lesson, id: lessonId },
      activity: { ...BASE.activity!, id: `${lessonId}-activity`, last_answer: null },
    }))
    vi.mocked(answerLearningActivity)
      .mockImplementationOnce(() => new Promise(() => undefined))
      .mockResolvedValueOnce({
        ...BASE,
        lesson: { ...BASE.lesson, id: 'mixtures-2' },
        activity: { ...BASE.activity!, id: 'mixtures-2-activity', last_answer: '30' },
      })
    const { result, rerender } = renderHook(
      ({ lessonId }) => useLearningFlow(lessonId),
      { initialProps: { lessonId: 'mixtures-1' }, wrapper },
    )
    await waitFor(() => expect(result.current.state?.lesson.id).toBe('mixtures-1'))

    act(() => result.current.changeAnswer('20'))
    act(() => result.current.submitAnswer())
    expect(result.current.isSubmitting).toBe(true)

    rerender({ lessonId: 'mixtures-2' })
    await waitFor(() => expect(result.current.state?.lesson.id).toBe('mixtures-2'))
    expect(result.current.isSubmitting).toBe(false)

    act(() => result.current.changeAnswer('30'))
    act(() => result.current.submitAnswer())
    await waitFor(() => expect(answerLearningActivity).toHaveBeenCalledTimes(2))
  })

  it('очищает поле только после перехода сервера на новую activity', async () => {
    vi.mocked(answerLearningActivity).mockResolvedValue({
      ...BASE,
      progress: { current: 3, total: 6, completed: 2 },
      activity: {
        ...BASE.activity!,
        id: 'guided-total',
        title: 'Теперь измени общую массу',
        last_answer: null,
        support: null,
        support_level: 0,
      },
      feedback: { is_correct: true, message: 'Верно.', is_duplicate: false },
    })
    const { result } = renderHook(() => useLearningFlow('mixtures-1'), { wrapper })
    await waitFor(() => expect(result.current.state).not.toBeNull())
    act(() => result.current.changeAnswer('20'))
    act(() => result.current.submitAnswer())

    await waitFor(() => expect(result.current.state?.activity?.id).toBe('guided-total'))
    expect(result.current.answer).toBe('')
  })

  it('сразу скрывает состояние прежнего ученика при смене identity', async () => {
    const secondStudent = {
      ...BASE,
      session_id: 20,
      activity: { ...BASE.activity!, id: 'student-2-activity', last_answer: '55' },
    }
    vi.mocked(startLearningLesson)
      .mockResolvedValueOnce(BASE)
      .mockResolvedValueOnce(secondStudent)
    vi.mocked(answerLearningActivity).mockImplementation(() => new Promise(() => undefined))
    const { result, rerender } = renderHook(
      ({ identity }) => useLearningFlow('mixtures-1', identity),
      { initialProps: { identity: 'student-1' }, wrapper },
    )
    await waitFor(() => expect(result.current.state?.session_id).toBe(10))
    act(() => result.current.changeAnswer('20'))
    act(() => result.current.submitAnswer())
    expect(result.current.isSubmitting).toBe(true)

    rerender({ identity: 'student-2' })
    expect(result.current.state).toBeNull()
    expect(result.current.answer).toBe('')
    expect(result.current.isSubmitting).toBe(false)
    await waitFor(() => expect(result.current.state?.session_id).toBe(20))
    expect(result.current.answer).toBe('55')
  })

  it('не откатывает mutation-state поздним stale /start', async () => {
    let resolveStale: ((state: LearningSessionState) => void) | undefined
    vi.mocked(startLearningLesson)
      .mockResolvedValueOnce(BASE)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveStale = resolve }))
    const advanced = {
      ...BASE,
      progress: { current: 3, total: 6, completed: 2 },
      activity: { ...BASE.activity!, id: 'guided-total', last_answer: null },
    }
    vi.mocked(answerLearningActivity).mockResolvedValue(advanced)
    const { result } = renderHook(() => useLearningFlow('mixtures-1', 'student-1'), { wrapper })
    await waitFor(() => expect(result.current.state?.activity?.id).toBe('guided-substance'))

    act(() => result.current.retryStart())
    await waitFor(() => expect(startLearningLesson).toHaveBeenCalledTimes(2))
    act(() => result.current.changeAnswer('20'))
    act(() => result.current.submitAnswer())
    await waitFor(() => expect(result.current.state?.activity?.id).toBe('guided-total'))

    await act(async () => resolveStale?.({
      ...BASE,
      activity: { ...BASE.activity! },
    }))
    await waitFor(() => expect(result.current.state?.activity?.id).toBe('guided-total'))
  })
})
