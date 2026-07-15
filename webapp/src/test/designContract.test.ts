/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProofTrace } from '../components/ProofTrace'

function source(path: string): string {
  return readFileSync(new URL(path, import.meta.url), 'utf8')
}

describe('AiPlus v11 «Лента решения» design contract', () => {
  it('использует Onest для чтения и Tektur только как короткий акцент', () => {
    const tokens = source('../theme/tokens.css')
    const fonts = source('../theme/fonts.css')

    expect(tokens).toContain("--font-sans: 'Onest'")
    expect(tokens).toContain("--font-display: 'Tektur'")
    expect(fonts).toContain("font-family: 'Onest'")
    expect(fonts).toContain("font-family: 'Tektur'")
    expect(`${tokens}\n${fonts}`).not.toMatch(/Literata|Alumni Sans|Unbounded/)
  })

  it('не возвращает exact lockup и costume mascot, используя code-native mark и белок', () => {
    const brand = source('../components/BrandMark.tsx')
    const mascot = source('../components/Mascot.tsx')

    expect(brand).toContain('brand-signature__seed')
    expect(brand).not.toContain('aiplus-logo-lockup')
    expect(mascot).toContain('squirrel-learner-420.webp')
    expect(mascot).toContain('squirrel-coach-420.webp')
    expect(mascot).toContain('squirrel-celebrate-420.webp')
    expect(mascot).not.toContain('mascot-coach-420.webp')
    expect(mascot).not.toContain('mascot-celebrate-1080.webp')
    expect(mascot).not.toContain('<svg')
  })

  it('делает drill, closure и srez focus flows без persistent navigation', () => {
    const shell = source('../components/AppShell.tsx')
    const navigation = source('../components/ApBottomBar.tsx')

    expect(shell).toContain('drill|closure|srez')
    expect(shell).toContain('{!isFocus && <ApBottomBar />}')
    expect(navigation).toContain("label: 'Путь'")
    expect(navigation).not.toContain("label: 'Сегодня'")
    expect(navigation).toContain("label: 'Прогресс'")
    expect(navigation).not.toContain("to: '/srez'")
  })

  it('оставляет единственный main landmark оболочке, включая loading и success states', () => {
    const shell = source('../components/AppShell.tsx')
    const focusPages = [
      source('../features/drill/DrillPage.tsx'),
      source('../features/closure/ClosurePage.tsx'),
      source('../features/srez/SrezPage.tsx'),
    ]

    expect(shell).toContain('<main')
    for (const page of focusPages) expect(page).not.toContain('<main')
  })

  it('фиксирует answer slot, solution rail и reduced-motion equivalent', () => {
    const css = source('../index.css')
    const active = source('../features/drill/RungActive.tsx')
    const solved = source('../features/drill/RungQuiet.tsx')

    expect(css).toContain('.bracket-slot')
    expect(css).toContain('.solution-ladder__node--active')
    expect(css).toContain('.solution-ladder__node--done')
    expect(css).toContain('.equation-commit')
    expect(css).toContain('@media (prefers-reduced-motion: reduce)')
    expect(active).toContain('data-state={hint')
    expect(solved).toContain('rung.submitted_value')
  })

  it('держит длинную математику в локальном viewport, а не в page overflow', () => {
    const css = source('../index.css')
    const math = source('../components/MathText.tsx')

    expect(css).toContain('.math-viewport')
    expect(css).toContain('overflow-x: auto')
    expect(math).toContain('math-scroll inline-block max-w-full')
  })

  it('рендерит ровно столько proof nodes, сколько пришло из данных', () => {
    render(createElement(ProofTrace, {
      ariaLabel: 'Три реальных шага',
      nodes: [
        { key: '1', label: 'Шаг 1', state: 'done' as const },
        { key: '2', label: 'Шаг 2', state: 'active' as const },
        { key: '3', label: 'Шаг 3', state: 'todo' as const },
      ],
    }))

    expect(screen.getAllByRole('listitem')).toHaveLength(3)
    expect(screen.getByRole('img', { name: 'Три реальных шага' })).toBeTruthy()
  })

  it('не считает mastery-band got закрытой задачей на hub', () => {
    const hub = source('../features/hub/HubPage.tsx')
    const meta = source('../features/hub/stateConfig.ts')

    expect(hub).not.toContain("state === 'got'")
    expect(meta).toContain("got: { label: 'Уверенно'")
    expect(meta).not.toContain("got: { label: 'Готово'")
  })

  it('не показывает internal topic id и fake duration в пользовательском тексте', () => {
    const topics = source('../features/hub/ProblemTopicsCard.tsx')
    const onboarding = source('../features/hub/HubOnboarding.tsx')

    expect(topics).not.toContain('topic.name_ru ?? topic.topic_id')
    expect(topics).toContain("topic.name_ru ?? 'Эта тема'")
    expect(onboarding).not.toMatch(/минут/)
  })
})
