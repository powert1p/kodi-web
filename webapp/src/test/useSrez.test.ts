import { createElement, type ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SrezTask } from '../lib/types'

vi.mock('../lib/api', () => ({
  startSrez: vi.fn(),
  answerSrez: vi.fn(),
}))

vi.mock('../lib/telemetry', () => ({ track: vi.fn() }))

import { answerSrez, startSrez } from '../lib/api'
import { useSrez } from '../features/srez/useSrez'

const TASKS: SrezTask[] = [
  {
    problem_id: 1,
    statement: '2 + 2',
    answer_type: 'number',
    node_title: 'Сложение',
    position: 1,
    total: 2,
  },
  {
    problem_id: 2,
    statement: '3 + 3',
    answer_type: 'number',
    node_title: 'Сложение',
    position: 2,
    total: 2,
  },
]

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return createElement(QueryClientProvider, { client }, children)
}

function wrapperFor(client: QueryClient) {
  return function SharedClientWrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children)
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(startSrez).mockResolvedValue(TASKS)
  vi.mocked(answerSrez).mockResolvedValue({ is_correct: true })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('useSrez feedback', () => {
  it('не переключает задачу автоматически после вердикта', async () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useSrez(), { wrapper })

    await vi.waitFor(() => expect(result.current.currentTask?.problem_id).toBe(1))

    act(() => result.current.submit('4'))
    await vi.waitFor(() => expect(result.current.phase).toBe('feedback'))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000)
    })

    expect(result.current.currentTask?.problem_id).toBe(1)
    expect(result.current.phase).toBe('feedback')
    vi.useRealTimers()
  })

  it('переходит дальше только после явного next()', async () => {
    const { result } = renderHook(() => useSrez(), { wrapper })

    await waitFor(() => expect(result.current.currentTask?.problem_id).toBe(1))
    act(() => result.current.submit('4'))
    await waitFor(() => expect(result.current.phase).toBe('feedback'))

    const next = (result.current as typeof result.current & { next?: () => void }).next
    expect(next).toBeTypeOf('function')
    act(() => next?.())

    expect(result.current.currentTask?.problem_id).toBe(2)
    expect(result.current.phase).toBe('answering')
  })

  it('создаёт новый набор задач при повторном входе в mini-srez', async () => {
    const secondTasks: SrezTask[] = [{
      problem_id: 3,
      statement: '4 + 4',
      answer_type: 'number',
      node_title: 'Сложение',
      position: 1,
      total: 1,
    }]
    vi.mocked(startSrez)
      .mockResolvedValueOnce(TASKS)
      .mockResolvedValueOnce(secondTasks)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const sharedWrapper = wrapperFor(client)

    const first = renderHook(() => useSrez(), { wrapper: sharedWrapper })
    await waitFor(() => expect(first.result.current.currentTask?.problem_id).toBe(1))
    first.unmount()

    const second = renderHook(() => useSrez(), { wrapper: sharedWrapper })
    await waitFor(() => expect(second.result.current.currentTask?.problem_id).toBe(3))

    expect(startSrez).toHaveBeenCalledTimes(2)
    second.unmount()
  })
})
