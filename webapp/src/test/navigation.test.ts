import { createElement } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApBottomBar } from '../components/ApBottomBar'
import { AppShell } from '../components/AppShell'

describe('основная навигация ученика', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('оставляет глобально только учебный путь и прогресс', () => {
    render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/'] },
        createElement(ApBottomBar),
      ),
    )

    const path = screen.getAllByRole('link', { name: 'Путь' })
    const progress = screen.getAllByRole('link', { name: 'Прогресс' })
    expect(path.every((link) => link.getAttribute('href') === '/')).toBe(true)
    expect(progress.every((link) => link.getAttribute('href') === '/analytics')).toBe(true)
    expect(screen.queryByRole('link', { name: 'Сегодня' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Срез' })).toBeNull()
  })

  it('сохраняет main landmark во всех состояниях focus route', () => {
    render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/drill/1'] },
        createElement(AppShell, null, createElement('section', null, 'Loading, error или success')),
      ),
    )

    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(document.querySelector('#main-content')).toBeTruthy()
  })

  it('скрывает нижнюю навигацию внутри урока', () => {
    render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/lesson/mixtures-1'] },
        createElement(AppShell, null, createElement('section', null, 'Один учебный шаг')),
      ),
    )

    expect(screen.queryByRole('navigation', { name: /основ/i })).toBeNull()
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('позволяет безопасно сменить ученика на общем устройстве', () => {
    const removeItem = vi.fn()
    vi.stubGlobal('localStorage', { removeItem })
    render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/'] },
        createElement(AppShell, null, createElement('section', null, 'Маршрут ученика')),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Сменить ученика' }))
    expect(removeItem).toHaveBeenCalledWith('kodi.jwt')
  })
})
