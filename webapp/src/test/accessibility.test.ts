import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ApTextField } from '../components/ApTextField'

describe('доступность form controls', () => {
  it('связывает текст ошибки ApTextField с input', () => {
    render(createElement(ApTextField, {
      id: 'email',
      label: 'Почта',
      error: 'Проверь адрес',
    }))

    const input = screen.getByLabelText('Почта')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.getAttribute('aria-describedby')).toBe('email-error')
    expect(document.querySelector('#email-error')?.textContent).toBe('Проверь адрес')
  })
})
