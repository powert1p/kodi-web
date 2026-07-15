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
})
