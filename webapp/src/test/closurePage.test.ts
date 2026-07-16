import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({ useWrongTask: vi.fn() }))
vi.mock('../features/closure/useClosure', () => ({ useClosure: vi.fn() }))

import { useWrongTask } from '../lib/api'
import { useClosure } from '../features/closure/useClosure'
import { ClosurePage } from '../features/closure/ClosurePage'

describe('ClosurePage recovery', () => {
  it('показывает retry вместо вечного skeleton при ошибке запуска', () => {
    const retryStart = vi.fn()
    vi.mocked(useWrongTask).mockReturnValue({
      data: {
        id: 7,
        problem_id: 77,
        primary_micro_skill: 'percent_of_number',
        topic_label: 'Проценты',
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useWrongTask>)
    vi.mocked(useClosure).mockReturnValue({
      status: 'error',
      problem: null,
      attempts: 0,
      lastAnswer: null,
      check: vi.fn(),
      resume: vi.fn(),
      retryStart,
    })

    render(createElement(
      MemoryRouter,
      { initialEntries: ['/closure/7'] },
      createElement(Routes, null,
        createElement(Route, { path: '/closure/:taskId', element: createElement(ClosurePage) }),
      ),
    ))

    expect(screen.getByRole('heading', { name: 'Не удалось подготовить проверку' })).toBeTruthy()
    screen.getByRole('button', { name: 'Попробовать ещё раз' }).click()
    expect(retryStart).toHaveBeenCalledTimes(1)
  })

  it('сохраняет экран успеха после удаления закрытой задачи из обновлённой очереди', () => {
    const task = {
      id: 7,
      problem_id: 77,
      primary_micro_skill: 'percent_of_number',
      topic_label: 'Проценты',
    }
    vi.mocked(useWrongTask).mockReturnValue({
      data: task,
      isLoading: false,
    } as unknown as ReturnType<typeof useWrongTask>)
    vi.mocked(useClosure).mockReturnValue({
      status: 'correct',
      problem: {
        problem_id: 78,
        node_id: 'percent',
        topic_label: 'Проценты',
        statement: 'Найди 20% от 250',
        micro_skill: 'percent_of_number',
        micro_skill_label: 'Процент от числа',
        xp: 30,
      },
      attempts: 0,
      lastAnswer: '50',
      check: vi.fn(),
      resume: vi.fn(),
      retryStart: vi.fn(),
    })

    const view = render(createElement(
      MemoryRouter,
      { initialEntries: ['/closure/7'] },
      createElement(Routes, null,
        createElement(Route, { path: '/closure/:taskId', element: createElement(ClosurePage) }),
      ),
    ))
    expect(screen.getByRole('heading', { name: 'Получилось самостоятельно.' })).toBeTruthy()

    vi.mocked(useWrongTask).mockReturnValue({
      data: undefined,
      isLoading: false,
    } as unknown as ReturnType<typeof useWrongTask>)
    view.rerender(createElement(
      MemoryRouter,
      { initialEntries: ['/closure/7'] },
      createElement(Routes, null,
        createElement(Route, { path: '/closure/:taskId', element: createElement(ClosurePage) }),
      ),
    ))

    expect(vi.mocked(useClosure).mock.calls.at(-1)?.[0]).toBe(77)
    expect(screen.getByRole('heading', { name: 'Получилось самостоятельно.' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Эта задача уже недоступна' })).toBeNull()
  })
})
