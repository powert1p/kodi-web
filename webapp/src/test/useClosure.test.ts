import { createElement, type ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({
  startVerification: vi.fn(),
  answerVerification: vi.fn(),
}))

vi.mock('../lib/telemetry', () => ({ track: vi.fn() }))

import { answerVerification, startVerification } from '../lib/api'
import { useClosure } from '../features/closure/useClosure'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return createElement(QueryClientProvider, { client }, children)
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(startVerification).mockResolvedValue({
    problem_id: 42,
    node_id: 'fractions',
    topic_label: 'Дроби',
    statement: '1/2 + 1/2',
    micro_skill: 'add_fractions',
    micro_skill_label: 'Сложение дробей',
    xp: 30,
  })
})

describe('useClosure submit state', () => {
  it('показывает checking до ответа сервера и блокирует повторную отправку', async () => {
    let resolveAnswer: ((value: { correct: boolean }) => void) | undefined
    vi.mocked(answerVerification).mockImplementation(
      () => new Promise((resolve) => { resolveAnswer = resolve }),
    )

    const { result } = renderHook(() => useClosure(7, 'add_fractions'), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('solving'))

    act(() => {
      result.current.check('1')
      result.current.check('1')
    })

    expect(result.current.status).toBe('checking')
    expect(answerVerification).toHaveBeenCalledTimes(1)

    await act(async () => resolveAnswer?.({ correct: true }))
    expect(result.current.status).toBe('correct')
  })

  it('позволяет повторить запуск проверки после сетевой ошибки', async () => {
    vi.mocked(startVerification)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({
        problem_id: 43,
        node_id: 'fractions',
        topic_label: 'Дроби',
        statement: '2/3 + 1/3',
        micro_skill: 'add_fractions',
        micro_skill_label: 'Сложение дробей',
        xp: 30,
      })

    const { result } = renderHook(() => useClosure(7, 'add_fractions'), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('error'))

    expect(result.current.problem).toBeNull()
    expect(result.current.retryStart).toBeTypeOf('function')
    act(() => result.current.retryStart())

    await waitFor(() => expect(result.current.status).toBe('solving'))
    expect(result.current.problem?.problem_id).toBe(43)
    expect(startVerification).toHaveBeenCalledTimes(2)
  })

  it('изолирует поздний ответ предыдущей задачи после смены problem id', async () => {
    let resolveOldAnswer: ((value: { correct: boolean }) => void) | undefined
    vi.mocked(answerVerification).mockImplementation(
      () => new Promise((resolve) => { resolveOldAnswer = resolve }),
    )
    vi.mocked(startVerification)
      .mockResolvedValueOnce({
        problem_id: 42,
        node_id: 'fractions',
        topic_label: 'Дроби',
        statement: '1/2 + 1/2',
        micro_skill: 'add_fractions',
        micro_skill_label: 'Сложение дробей',
        xp: 30,
      })
      .mockResolvedValueOnce({
        problem_id: 84,
        node_id: 'percent',
        topic_label: 'Проценты',
        statement: '10% от 50',
        micro_skill: 'percent_of_number',
        micro_skill_label: 'Процент от числа',
        xp: 30,
      })

    const { result, rerender } = renderHook(
      ({ id }) => useClosure(id, 'add_fractions'),
      { initialProps: { id: 7 }, wrapper },
    )
    await waitFor(() => expect(result.current.problem?.problem_id).toBe(42))
    act(() => result.current.check('1'))
    expect(result.current.status).toBe('checking')

    rerender({ id: 8 })
    expect(result.current.status).toBe('loading')
    expect(result.current.problem).toBeNull()
    await waitFor(() => expect(result.current.problem?.problem_id).toBe(84))

    await act(async () => resolveOldAnswer?.({ correct: true }))
    expect(result.current.status).toBe('solving')
    expect(result.current.problem?.problem_id).toBe(84)
    expect(result.current.lastAnswer).toBeNull()
  })

  it('очищает завершённую closure при переходе на отсутствующую задачу', async () => {
    vi.mocked(answerVerification).mockResolvedValue({ correct: true })
    const { result, rerender } = renderHook(
      ({ id }) => useClosure(id, 'add_fractions'),
      { initialProps: { id: 7 }, wrapper },
    )
    await waitFor(() => expect(result.current.status).toBe('solving'))
    act(() => result.current.check('1'))
    await waitFor(() => expect(result.current.status).toBe('correct'))

    rerender({ id: 0 })

    expect(result.current.status).toBe('loading')
    expect(result.current.problem).toBeNull()
    expect(result.current.lastAnswer).toBeNull()
  })
})
