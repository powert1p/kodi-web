import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { JourneyPage } from '../features/journey/JourneyPage'
import {
  JourneyApiError,
  type JourneyNextStep,
  type JourneyProblem,
  type JourneyState,
  type PhotoTaskStep,
} from '../lib/journeyApi'

const journeyApi = vi.hoisted(() => ({
  fetchJourney: vi.fn(),
  saveJourneyProfile: vi.fn(),
  saveJourneyProfileDraft: vi.fn(),
  continueJourney: vi.fn(),
  submitDiagnosticAnswer: vi.fn(),
  requestJourneyHelp: vi.fn(),
  submitGuidedAnswer: vi.fn(),
  submitTypedAnswer: vi.fn(),
  uploadJourneyPhoto: vi.fn(),
  retryJourneyPhoto: vi.fn(),
}))

const api = vi.hoisted(() => ({
  postConsent: vi.fn(),
  sendTutorMessage: vi.fn(),
  useLearningIdentity: vi.fn(() => 'student-a'),
}))

const imageApi = vi.hoisted(() => ({
  compressForUpload: vi.fn(async (file: File) => file),
}))

vi.mock('../lib/journeyApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/journeyApi')>('../lib/journeyApi')
  return { ...actual, ...journeyApi }
})

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return {
    ...actual,
    postConsent: api.postConsent,
    sendTutorMessage: api.sendTutorMessage,
    useLearningIdentity: api.useLearningIdentity,
  }
})

vi.mock('../lib/image', async () => {
  const actual = await vi.importActual<typeof import('../lib/image')>('../lib/image')
  return { ...actual, compressForUpload: imageApi.compressForUpload }
})

function state(nextStep: JourneyState['next_step'], revision = 0): JourneyState {
  return {
    journey_id: 11,
    revision,
    next_step: nextStep,
    context: {
      exam_map: {
        title: 'Первый день конкурсного отбора NIS',
        scope_note: 'Готовим к двум математическим блокам.',
        day_one: [],
      },
      route: { topics: [], index: 0, completed: [] },
    },
  }
}

type WorkspaceStep = Extract<
  JourneyNextStep,
  {
    type:
      | 'independent_task'
      | 'transfer_task'
      | 'typed_processing'
      | 'guided_processing'
      | 'photo_processing'
      | 'guided_step'
      | 'photo_feedback'
      | 'photo_recovery'
      | 'transfer_feedback'
  }
>

function workspaceState(nextStep: WorkspaceStep, revision = 0): JourneyState {
  const mode = nextStep.type === 'transfer_task' || nextStep.type === 'transfer_feedback'
    ? 'transfer'
    : 'independent'
  const evidenceStatus = nextStep.type === 'photo_processing' || nextStep.type === 'typed_processing' || nextStep.type === 'guided_processing'
    ? 'processing'
    : nextStep.type === 'guided_step'
      ? 'guided'
      : nextStep.type === 'photo_recovery'
        ? 'preserved'
        : nextStep.type === 'photo_feedback' || nextStep.type === 'transfer_feedback'
          ? 'checked'
          : 'empty'
  const contextKind = nextStep.type === 'photo_processing' || nextStep.type === 'typed_processing' || nextStep.type === 'guided_processing'
    ? 'processing'
    : nextStep.type === 'guided_step'
      ? 'guided'
      : nextStep.type === 'photo_recovery'
        ? 'uncertain'
        : nextStep.type === 'photo_feedback' || nextStep.type === 'transfer_feedback'
          ? 'feedback'
          : 'closed'
  return {
    ...state(nextStep, revision),
    workspace_version: 1,
    task: {
      journey_id: 11,
      problem_id: nextStep.problem.id,
      topic: nextStep.problem.topic,
      mode,
      statement: nextStep.problem.statement,
      position: 3,
    },
    learner_evidence: {
      kind: nextStep.type === 'typed_processing' || nextStep.type === 'guided_processing' ? 'typed' : 'photo',
      status: evidenceStatus,
      label: nextStep.type === 'typed_processing' || nextStep.type === 'guided_processing'
        ? nextStep.preserved_answer.value
        : evidenceStatus === 'checked' || evidenceStatus === 'preserved' ? 'solution.jpg' : null,
    },
    context_layer: {
      kind: contextKind,
      verdict: nextStep.type === 'photo_recovery'
        ? 'uncertain'
        : nextStep.type === 'photo_feedback' || nextStep.type === 'transfer_feedback'
          ? nextStep.verdict === 'correct' ? 'correct' : 'needs_revision'
          : null,
      recovery_reason: nextStep.type === 'photo_recovery' ? nextStep.reason : null,
    },
    response: {
      default_mode: nextStep.type === 'typed_processing' ? 'typed' : 'photo',
      typed_available: nextStep.type === 'independent_task' || nextStep.type === 'transfer_task',
      help_available: nextStep.type === 'independent_task',
    },
    support: { used: nextStep.type === 'guided_step', highest_hint_rung: nextStep.type === 'guided_step' ? 1 : 0 },
  }
}

function renderJourney(initialState: JourneyState) {
  journeyApi.fetchJourney.mockResolvedValue(initialState)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const tree = () => createElement(
    QueryClientProvider,
    { client },
    createElement(MemoryRouter, null, createElement(JourneyPage)),
  )
  const result = render(tree())
  return { ...result, rerenderJourney: () => result.rerender(tree()) }
}

describe('server-owned учебный journey', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.useLearningIdentity.mockReturnValue('student-a')
    api.postConsent.mockResolvedValue(undefined)
    api.sendTutorMessage.mockResolvedValue({ session_id: 1, reply: '', history: [] })
    document.documentElement.scrollTop = 0
  })

  it('начинает с адаптации, а не с задачи', async () => {
    const profileStep = {
      type: 'profile',
      student: { name: 'Саша', grade: 6 },
      title: 'Начнём с тебя',
      description: 'Сначала настроим цель, затем определим стартовый уровень.',
      screen: 0,
      substep: 0,
      screen_count: 4,
      draft: {
        target: 'nis-grade-7',
        weekly_goal: 4,
        session_minutes: 30,
        target_window: 'spring-2027',
        prep_experience: 'new',
        weak_topics: [],
        strong_topics: [],
        mock_math_band: 'not-taken',
        language: 'ru',
      },
      primary_action: 'Настроить подготовку',
    } satisfies Extract<JourneyState['next_step'], { type: 'profile' }>
    const profile = state(profileStep)
    journeyApi.saveJourneyProfileDraft.mockImplementation(async (body) => {
      const { revision, screen: draftScreen, substep, ...draft } = body
      return state({
        ...profileStep,
        screen: draftScreen,
        substep,
        draft,
      }, revision + 1)
    })
    journeyApi.saveJourneyProfile.mockResolvedValue(state({
      type: 'exam_map',
      title: 'Что будет на отборе NIS',
      scope_note: 'Готовим к двум математическим блокам.',
      primary_action: 'Перейти к диагностике',
    }, 1))

    renderJourney(profile)

    expect(await screen.findByRole('heading', { name: 'Начнём с тебя' })).toBeTruthy()
    expect(screen.queryByText('Сфотографировать решение')).toBeNull()
    expect(screen.getByText('Саша, 6 класс')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Весна 2027' }))
    document.documentElement.scrollTop = 480
    fireEvent.click(screen.getByRole('button', { name: 'Продолжить к ритму' }))

    expect(await screen.findByRole('heading', { name: 'Выберем спокойный ритм' })).toBeTruthy()
    expect(document.documentElement.scrollTop).toBe(0)
    fireEvent.click(screen.getByRole('radio', { name: '3 раза' }))
    fireEvent.click(screen.getByRole('button', { name: 'Дальше' }))
    fireEvent.click(await screen.findByRole('radio', { name: '30 минут' }))
    fireEvent.click(screen.getByRole('button', { name: 'Дальше' }))
    fireEvent.click(await screen.findByRole('radio', { name: 'Сам' }))
    fireEvent.click(screen.getByRole('button', { name: 'Продолжить к темам' }))

    expect(await screen.findByRole('heading', { name: 'Что учесть в диагностике' })).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Проценты: сложно' }))
    fireEvent.click(screen.getByRole('radio', { name: 'Текстовые уравнения: получается' }))
    fireEvent.click(screen.getByRole('button', { name: 'Продолжить' }))

    expect(await screen.findByRole('heading', { name: 'Есть результат пробника?' })).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: '21–30 верных из 40' }))
    fireEvent.click(screen.getByRole('button', { name: 'Построить диагностику' }))

    expect(journeyApi.saveJourneyProfile).toHaveBeenCalledWith({
      revision: 5,
      target: 'nis-grade-7',
      weekly_goal: 3,
      session_minutes: 30,
      target_window: 'spring-2027',
      prep_experience: 'self',
      weak_topics: ['PC05'],
      strong_topics: ['EQ04'],
      mock_math_band: '21-30',
      language: 'ru',
    })
    expect(await screen.findByRole('heading', { name: 'Что будет на отборе NIS' })).toBeTruthy()
    expect(journeyApi.saveJourneyProfileDraft).toHaveBeenNthCalledWith(2, expect.objectContaining({
      screen: 1,
      substep: 1,
      weekly_goal: 3,
    }))
    expect(journeyApi.saveJourneyProfileDraft).toHaveBeenNthCalledWith(3, expect.objectContaining({
      screen: 1,
      substep: 2,
      session_minutes: 30,
    }))
  })

  it('после stale revision применяет server state и явно предлагает загрузить свежую версию', async () => {
    const initial = state({
      type: 'diagnostic_intro',
      title: 'Начать диагностику',
      description: 'Пять опорных задач.',
      estimated_minutes: 8,
      primary_action: 'Начать диагностику',
    }, 7)
    const embedded = state({
      type: 'diagnostic_question',
      title: 'Снимок из конфликта',
      progress: { answered: 0, current: 1, planned: 5 },
      question: { id: 321, statement: 'Найди 20% от 300.', answer_type: 'number' },
      primary_action: 'Проверить ответ',
    }, 8)
    const authoritative = state({
      type: 'diagnostic_question',
      title: 'Актуальная задача сервера',
      progress: { answered: 0, current: 1, planned: 5 },
      question: { id: 322, statement: 'Найди 25% от 400.', answer_type: 'number' },
      primary_action: 'Проверить ответ',
    }, 9)
    journeyApi.continueJourney.mockRejectedValue(new JourneyApiError(
      409,
      'Экран уже изменился.',
      'stale_revision',
      embedded,
    ))

    renderJourney(initial)
    await screen.findByRole('heading', { name: 'Начать диагностику' })
    journeyApi.fetchJourney.mockResolvedValue(authoritative)
    fireEvent.click(screen.getByRole('button', { name: 'Начать диагностику' }))

    expect((await screen.findByRole('alert')).textContent).toContain('Экран уже изменился.')
    expect(await screen.findByText('Найди 20% от 300.')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Начать диагностику' })).toBeNull()
    expect(journeyApi.fetchJourney).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Загрузить актуальный маршрут' }))

    expect(await screen.findByText('Найди 25% от 400.')).toBeTruthy()
    expect(journeyApi.fetchJourney).toHaveBeenCalledTimes(2)
  })

  it('на самостоятельной задаче показывает полное условие, одно фото и explicit help', async () => {
    const problem: JourneyProblem = {
      id: 44,
      content_idx: 1765,
      node_id: 'PC06',
      statement: 'Смешали 300 г раствора с массовой долей соли 25% и 200 г воды. Найди концентрацию.',
      topic: { id: 'PC06', title: 'Смеси и концентрации' },
    }
    const independent = state({
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу полностью на бумаге и отправь одно фото всей страницы.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 9)
    journeyApi.requestJourneyHelp.mockResolvedValue(state({
      type: 'guided_step',
      title: 'Разберём эту же задачу',
      problem,
      step: {
        number: 1,
        total: 3,
        instruction: 'Найди массу соли в исходном растворе.',
        prompt: 'Сколько соли было сначала?',
        format_hint: 'Запиши массу в граммах.',
        example: '20 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень. Его подтвердит новая самостоятельная задача.',
      primary_action: 'Проверить шаг',
    }, 10))

    renderJourney(independent)

    expect(await screen.findByText(problem.statement)).toBeTruthy()
    expect(screen.getByLabelText('Фото всего решения')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Не знаю, как решать' }))

    expect(journeyApi.requestJourneyHelp).toHaveBeenCalledWith({ revision: 9, problem_id: 44 })
    expect(await screen.findByRole('heading', { name: 'Разберём эту же задачу' })).toBeTruthy()
    expect(screen.queryByLabelText('Фото всего решения')).toBeNull()
  })

  it('после AI-confirmed incorrect оставляет typed, photo и help на той же задаче', async () => {
    const problem: JourneyProblem = {
      id: 144,
      content_idx: 1765,
      node_id: 'FR03',
      statement: 'Не вычисляя, определи, какая дробь дальше от 1/2: 3/7 или 4/9?',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Докажи свой выбор',
      mode: 'independent',
      problem,
      instruction: 'Реши полностью на бумаге и отправь одно фото всей страницы.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    } satisfies PhotoTaskStep
    journeyApi.submitTypedAnswer.mockResolvedValue(workspaceState({
      ...task,
      typed_feedback: {
        verdict: 'incorrect',
        message: 'Проверь вычисления и попробуй ещё раз.',
        error_focus: 'calculation',
        counts_for_mastery: false,
      },
    }, 10))

    renderJourney(workspaceState(task, 9))

    expect(await screen.findByText(problem.statement)).toBeTruthy()
    const taskAnchor = screen.getByTestId('task-anchor')
    const workspace = screen.getByTestId('learning-workspace')
    expect(workspace.querySelectorAll('[data-primary-action]')).toHaveLength(1)
    document.documentElement.scrollTop = 420
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '3/7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    await waitFor(() => expect(journeyApi.submitTypedAnswer).toHaveBeenCalledWith(expect.objectContaining({
      revision: 9,
      problem_id: 144,
      answer: '3/7',
    })))
    expect(await screen.findByRole('heading', { name: 'Проверь вычисления' })).toBeTruthy()
    expect(screen.getByText(/Исправь ответ или отправь фото\. Можно также попросить помощь/)).toBeTruthy()
    expect(screen.getByTestId('response-dock').textContent).toContain(
      'Проверь вычисления и попробуй ещё раз. Исправь ответ или отправь фото.',
    )
    const feedback = screen.getByRole('status')
    expect(feedback.getAttribute('aria-live')).toBe('polite')
    expect(feedback.getAttribute('tabindex')).toBe('-1')
    await waitFor(() => expect(document.activeElement).toBe(feedback))
    expect(screen.getByTestId('task-anchor')).toBe(taskAnchor)
    expect(document.documentElement.scrollTop).toBe(420)
    expect(workspace.querySelectorAll('[data-primary-action]')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Отправить фото' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Не знаю, как начать' })).toBeTruthy()
  })

  it('после reload восстанавливает проверенный typed-ответ в той же задаче', async () => {
    const problem: JourneyProblem = {
      id: 159,
      content_idx: 1780,
      node_id: 'FR03',
      statement: 'Сравни 5/8 и 7/12.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Дай итоговый ответ или отправь фото.',
      photo_required: false,
      help_available: true,
      photo_consent_required: false,
      typed_feedback: {
        verdict: 'incorrect',
        message: 'Проверь вычисления и попробуй ещё раз.',
        error_focus: 'calculation',
        counts_for_mastery: true,
      },
      preserved_answer: { value: '7/12' },
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep

    renderJourney(workspaceState(task, 23))

    expect(await screen.findByRole('heading', { name: 'Проверь вычисления' })).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Короткий ответ' }) as HTMLInputElement).value).toBe('7/12')
    expect(screen.getByTestId('workbook-task-summary').textContent).toContain('7/12 · ответ проверен')
    expect(screen.getByRole('button', { name: 'Проверить ответ' })).toBeTruthy()
  })

  it('после user-перехода в typed mode в short landscape прокручивает форму и фокусирует input', async () => {
    const originalScrollIntoView = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView')
    const originalMatchMedia = Object.getOwnPropertyDescriptor(window, 'matchMedia')
    const scrollIntoView = vi.fn()
    const matchMedia = vi.fn(() => ({ matches: true }))
    const focus = vi.spyOn(HTMLInputElement.prototype, 'focus')
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: matchMedia,
    })

    try {
      const problem: JourneyProblem = {
        id: 147,
        content_idx: 1768,
        node_id: 'FR03',
        statement: 'Сравни 8/13 и 3/5.',
        topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
      }
      const task = {
        type: 'independent_task',
        title: 'Реши самостоятельно',
        mode: 'independent',
        problem,
        instruction: 'Реши задачу целиком.',
        photo_required: true,
        help_available: true,
        photo_consent_required: false,
        primary_action: 'Отправить фото',
      } satisfies PhotoTaskStep

      renderJourney(workspaceState(task, 13))

      await screen.findByText(problem.statement)
      fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
      const input = await screen.findByRole('textbox', { name: 'Короткий ответ' })
      const form = input.closest('form')
      if (!form) throw new Error('Typed-форма не отрендерилась.')

      await waitFor(() => expect(document.activeElement).toBe(input))
      expect(matchMedia).toHaveBeenCalledWith('(orientation: landscape) and (max-height: 34rem)')
      expect(scrollIntoView).toHaveBeenCalledWith({ block: 'end' })
      expect(scrollIntoView.mock.instances).toContain(form)
      expect(focus).toHaveBeenCalledWith({ preventScroll: true })
      expect(focus.mock.instances).toContain(input)
    } finally {
      focus.mockRestore()
      if (originalScrollIntoView) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScrollIntoView)
      else Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
      if (originalMatchMedia) Object.defineProperty(window, 'matchMedia', originalMatchMedia)
      else Reflect.deleteProperty(window, 'matchMedia')
    }
  })

  it('после AI-confirmed correct открывает transfer-задачу и переводит focus на неё', async () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
    const problem: JourneyProblem = {
      id: 148,
      content_idx: 1769,
      node_id: 'FR03',
      statement: 'Сравни 7/10 и 2/3.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const nextProblem: JourneyProblem = {
      id: 149,
      content_idx: 1770,
      node_id: 'FR03',
      statement: 'Сравни 11/15 и 3/4.',
      topic: problem.topic,
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу целиком.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    journeyApi.submitTypedAnswer.mockResolvedValue(workspaceState({
      type: 'transfer_task',
      title: 'Проверь перенос',
      mode: 'transfer',
      problem: nextProblem,
      instruction: 'Реши новую задачу самостоятельно.',
      photo_required: true,
      help_available: false,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    }, 15))

    renderJourney(workspaceState(task, 14))

    await screen.findByText(problem.statement)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '7/10' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    await waitFor(() => expect(journeyApi.submitTypedAnswer).toHaveBeenCalledWith(expect.objectContaining({
      revision: 14,
      problem_id: 148,
      answer: '7/10',
    })))
    expect(await screen.findByText(nextProblem.statement)).toBeTruthy()
    expect(screen.getByText('Ответ принят. Открываем новую задачу.')).toBeTruthy()
    await waitFor(() => expect(document.activeElement).toBe(
      screen.getByRole('heading', { name: 'Проверь перенос' }),
    ))
    expect(scrollIntoView.mock.instances.at(-1)).toBe(screen.getByTestId('task-anchor'))
    expect(screen.queryByText(/подтверди.*фото/i)).toBeNull()
  })

  it('при stale typed state применяет серверный экран и сохраняет набранный ответ', async () => {
    const problem: JourneyProblem = {
      id: 150,
      content_idx: 1771,
      node_id: 'FR03',
      statement: 'Сравни 5/8 и 3/5.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу целиком.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    const staleState = workspaceState({
      ...task,
      typed_feedback: {
        verdict: 'incorrect',
        message: 'На сервере уже есть более свежая проверка.',
        error_focus: 'calculation',
        counts_for_mastery: false,
      },
    }, 16)
    journeyApi.submitTypedAnswer.mockRejectedValue(new JourneyApiError(
      409,
      'Экран уже изменился.',
      'stale_revision',
      staleState,
    ))

    renderJourney(workspaceState(task, 15))

    await screen.findByText(problem.statement)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    const input = screen.getByRole('textbox', { name: 'Короткий ответ' })
    fireEvent.change(input, { target: { value: '5/8' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    expect(await screen.findByRole('heading', { name: 'Проверь вычисления' })).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Короткий ответ' }) as HTMLInputElement).value).toBe('5/8')
    expect(screen.getByText('На сервере уже есть более свежая проверка.')).toBeTruthy()
  })

  it('при stale typed state с другой задачей сохраняет ответ отдельно до явного восстановления', async () => {
    const problem: JourneyProblem = {
      id: 154,
      content_idx: 1775,
      node_id: 'FR03',
      statement: 'Сравни 2/9 и 1/4.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const nextProblem: JourneyProblem = {
      id: 155,
      content_idx: 1776,
      node_id: 'FR03',
      statement: 'Сравни 5/12 и 3/7.',
      topic: problem.topic,
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу целиком.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    const nextTask = {
      ...task,
      problem: nextProblem,
    } satisfies PhotoTaskStep
    journeyApi.submitTypedAnswer.mockRejectedValue(new JourneyApiError(
      409,
      'Экран уже изменился.',
      'stale_revision',
      workspaceState(nextTask, 22),
    ))

    renderJourney(workspaceState(task, 21))

    await screen.findByText(problem.statement)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '2/9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    expect(await screen.findByText(nextProblem.statement)).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('Открыта другая задача.')
    expect(screen.getByRole('button', { name: 'Восстановить ответ в поле' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    const input = screen.getByRole('textbox', { name: 'Короткий ответ' }) as HTMLInputElement
    expect(input.value).toBe('')

    fireEvent.click(screen.getByRole('button', { name: 'Восстановить ответ в поле' }))
    await waitFor(() => expect((screen.getByRole('textbox', { name: 'Короткий ответ' }) as HTMLInputElement).value).toBe('2/9'))
  })

  it('сохраняет durable attempt id и черновик после ai_unavailable и http_429 typed-проверки', async () => {
    const problem: JourneyProblem = {
      id: 151,
      content_idx: 1772,
      node_id: 'FR03',
      statement: 'Сравни 4/7 и 5/9.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const nextProblem: JourneyProblem = {
      id: 152,
      content_idx: 1773,
      node_id: 'FR03',
      statement: 'Сравни 7/9 и 3/4.',
      topic: problem.topic,
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу целиком.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    const unavailableState = workspaceState({
      ...task,
      typed_feedback: {
        verdict: 'unsure',
        message: 'Проверка временно недоступна. Повтори проверку или отправь фото.',
        error_focus: 'unknown',
        counts_for_mastery: false,
      },
    }, 17)
    journeyApi.submitTypedAnswer
      .mockRejectedValueOnce(new JourneyApiError(
        503,
        'Проверка ответа временно недоступна.',
        'ai_unavailable',
        unavailableState,
      ))
      .mockRejectedValueOnce(new JourneyApiError(429, 'Слишком много попыток. Подожди минуту.', 'http_429'))
      .mockResolvedValueOnce(workspaceState({
        type: 'transfer_task',
        title: 'Проверь перенос',
        mode: 'transfer',
        problem: nextProblem,
        instruction: 'Реши новую задачу самостоятельно.',
        photo_required: true,
        help_available: false,
        photo_consent_required: false,
        primary_action: 'Отправить фото',
      }, 18))

    renderJourney(workspaceState(task, 17))

    await screen.findByText(problem.statement)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '4/7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    expect(await screen.findByText('Проверка ответа временно недоступна.')).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Короткий ответ' }) as HTMLInputElement).value).toBe('4/7')
    const uncertaintyFeedback = screen.getByRole('status')
    expect(uncertaintyFeedback.textContent).toContain('Проверим другим способом')
    await waitFor(() => expect(document.activeElement).toBe(uncertaintyFeedback))
    fireEvent.click(screen.getByRole('button', { name: 'Повторить проверку' }))
    expect(await screen.findByText('Слишком много попыток. Подожди минуту.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Повторить проверку' }))

    await waitFor(() => expect(journeyApi.submitTypedAnswer).toHaveBeenCalledTimes(3))
    const [first, second, third] = journeyApi.submitTypedAnswer.mock.calls
    if (!first || !second || !third) {
      throw new Error('Ожидались три попытки отправки typed-ответа.')
    }
    expect(second[0].client_attempt_id).toBe(first[0].client_attempt_id)
    expect(third[0].client_attempt_id).toBe(first[0].client_attempt_id)
    expect(await screen.findByText(nextProblem.statement)).toBeTruthy()
  })

  it('блокирует двойную отправку typed-ответа до ответа сервера', async () => {
    const problem: JourneyProblem = {
      id: 153,
      content_idx: 1774,
      node_id: 'FR03',
      statement: 'Сравни 9/14 и 2/3.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу целиком.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    let resolveSubmission!: (value: JourneyState) => void
    journeyApi.submitTypedAnswer.mockImplementation(() => new Promise<JourneyState>((resolve) => {
      resolveSubmission = resolve
    }))

    renderJourney(workspaceState(task, 19))

    await screen.findByText(problem.statement)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '9/14' } })
    const submit = screen.getByRole('button', { name: 'Проверить ответ' })
    fireEvent.click(submit)
    fireEvent.click(submit)

    await waitFor(() => expect(journeyApi.submitTypedAnswer).toHaveBeenCalledTimes(1))
    expect((screen.getByRole('button', { name: 'Проверяем…' }) as HTMLButtonElement).disabled).toBe(true)
    resolveSubmission(workspaceState(task, 20))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Проверить ответ' }) as HTMLButtonElement).disabled).toBe(false))
  })

  it('после reload показывает сохранённый typed-ответ и сам открывает результат проверки', async () => {
    const problem: JourneyProblem = {
      id: 154,
      content_idx: 1775,
      node_id: 'FR03',
      statement: 'Сравни 5/6 и 7/9.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const processing = {
      type: 'typed_processing',
      title: 'Проверяем ответ',
      problem,
      message: 'AI сопоставляет ответ с условием. Экран можно обновить.',
      preserved_answer: { value: '5/6' },
      primary_action: 'Проверить статус',
    } satisfies WorkspaceStep
    const nextProblem: JourneyProblem = {
      ...problem,
      id: 155,
      content_idx: 1776,
      statement: 'Расположи 3/5, 7/10 и 2/3 по возрастанию.',
    }
    const advanced = workspaceState({
      type: 'transfer_task',
      title: 'Новая задача на перенос',
      mode: 'transfer',
      problem: nextProblem,
      instruction: 'Реши самостоятельно.',
      photo_required: false,
      help_available: false,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    }, 21)

    renderJourney(workspaceState(processing, 20))

    expect(await screen.findByRole('heading', { name: 'Проверяем ответ' })).toBeTruthy()
    expect(screen.getByTestId('workbook-task-summary').textContent).toContain('5/6')
    expect((screen.getByRole('button', { name: 'AI проверяет ответ…' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.queryByLabelText('Фото всего решения')).toBeNull()

    journeyApi.fetchJourney.mockResolvedValue(advanced)
    expect(await screen.findByText(nextProblem.statement, {}, { timeout: 3500 })).toBeTruthy()
    expect(journeyApi.fetchJourney.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('после потери HTTP-ответа сам восстанавливает server state typed-проверки', async () => {
    const problem: JourneyProblem = {
      id: 156,
      content_idx: 1777,
      node_id: 'FR03',
      statement: 'Какая дробь больше: 11/15 или 3/4?',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Дай итоговый ответ или отправь фото.',
      photo_required: false,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    } satisfies PhotoTaskStep
    const processing = workspaceState({
      type: 'typed_processing',
      title: 'Проверяем ответ',
      problem,
      message: 'Ответ сохранён, AI продолжает проверку.',
      preserved_answer: { value: '3/4' },
      primary_action: 'Проверить статус',
    } satisfies WorkspaceStep, 31)
    const nextProblem: JourneyProblem = {
      ...problem,
      id: 157,
      content_idx: 1778,
      statement: 'Сравни 13/18 и 5/7.',
    }
    const advanced = workspaceState({
      type: 'transfer_task',
      title: 'Новая задача на перенос',
      mode: 'transfer',
      problem: nextProblem,
      instruction: 'Реши самостоятельно.',
      photo_required: false,
      help_available: false,
      photo_consent_required: false,
      primary_action: 'Отправить фото',
    }, 32)
    journeyApi.submitTypedAnswer.mockRejectedValue(new Error('HTTP-ответ потерян'))

    renderJourney(workspaceState(task, 30))
    await screen.findByText(problem.statement)
    journeyApi.fetchJourney.mockResolvedValueOnce(processing).mockResolvedValue(advanced)
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Короткий ответ' }), { target: { value: '3/4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить ответ' }))

    expect(await screen.findByRole('heading', { name: 'Проверяем ответ' })).toBeTruthy()
    expect(await screen.findByText(nextProblem.statement, {}, { timeout: 3500 })).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('не сбрасывает scroll и focus при смене задачи внутри workspace', async () => {
    const firstProblem: JourneyProblem = {
      id: 146,
      content_idx: 1767,
      node_id: 'FR03',
      statement: 'Докажи, что 7/12 больше 4/7.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const nextProblem: JourneyProblem = {
      id: 147,
      content_idx: 1768,
      node_id: 'FR03',
      statement: 'Сравни 5/9 и 6/11 и обоснуй ответ.',
      topic: firstProblem.topic,
    }
    journeyApi.continueJourney.mockResolvedValue(workspaceState({
      type: 'transfer_task',
      title: 'Новая задача на перенос',
      mode: 'transfer',
      problem: nextProblem,
      instruction: 'Реши полностью на бумаге.',
      photo_required: true,
      help_available: false,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 13))
    renderJourney(workspaceState({
      type: 'photo_feedback',
      problem: firstProblem,
      verdict: 'correct',
      message: 'Полное решение подтверждено.',
      mastery: { value: 0.72, threshold: 0.85, reached: false },
      primary_action: 'Решить новую задачу',
    }, 12))

    await screen.findByText(firstProblem.statement)
    const focusSentinel = document.createElement('input')
    focusSentinel.setAttribute('aria-label', 'Внешний focus sentinel')
    document.body.append(focusSentinel)
    focusSentinel.focus()
    document.documentElement.scrollTop = 420
    document.body.scrollTop = 180

    fireEvent.click(screen.getByRole('button', { name: 'Решить новую задачу' }))

    expect(await screen.findByText(nextProblem.statement)).toBeTruthy()
    expect(document.documentElement.scrollTop).toBe(420)
    expect(document.body.scrollTop).toBe(180)
    expect(document.activeElement).toBe(focusSentinel)
    focusSentinel.remove()
  })

  it('открывает контекстного AI-помощника без ухода со страницы задачи', async () => {
    const problem: JourneyProblem = {
      id: 145,
      content_idx: 1766,
      node_id: 'FR03',
      statement: 'Объясни, почему 5/8 больше 3/5.',
      topic: { id: 'FR03', title: 'Сравнение и смысл дробей' },
    }
    const task = {
      type: 'independent_task',
      title: 'Обоснуй сравнение',
      mode: 'independent',
      problem,
      instruction: 'Покажи ход рассуждения.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    } satisfies PhotoTaskStep
    api.sendTutorMessage.mockResolvedValue({
      session_id: 81,
      reply: 'К какому общему знаменателю удобно привести обе дроби?',
      history: [
        { role: 'user', content: 'Не понимаю, с чего начать.' },
        { role: 'assistant', content: 'К какому общему знаменателю удобно привести обе дроби?' },
      ],
    })

    renderJourney(workspaceState(task, 11))
    await screen.findByText(problem.statement)
    const trigger = screen.getByRole('button', { name: 'Спросить AI-помощника' })
    fireEvent.click(trigger)

    expect(screen.getAllByText(problem.statement)).toHaveLength(2)
    expect(await screen.findByRole('heading', { name: 'Разберём мысль, не ответ' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Вернуться к задаче' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Сфотографировать решение' })).toBeNull()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(await screen.findByRole('heading', { name: 'Сначала реши задачу целиком' })).toBeTruthy()
    const restoredTrigger = screen.getByRole('button', { name: 'Спросить AI-помощника' })
    await waitFor(() => expect(document.activeElement).toBe(restoredTrigger))
    fireEvent.click(restoredTrigger)
    const input = screen.getByRole('textbox', { name: 'Твой вопрос' })
    await waitFor(() => expect(document.activeElement).toBe(input))
    fireEvent.change(input, { target: { value: 'Не понимаю, с чего начать.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить вопрос' }))

    await waitFor(() => expect(api.sendTutorMessage).toHaveBeenCalledWith(145, 'Не понимаю, с чего начать.', 1766, null))
    expect(await screen.findByText('К какому общему знаменателю удобно привести обе дроби?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Вернуться к задаче' }))
    expect(await screen.findByRole('heading', { name: 'Сначала реши задачу целиком' })).toBeTruthy()
    await waitFor(() => expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Спросить AI-помощника' }),
    ))
  })

  it('просит согласие взрослого внутри той же задачи и не прячет условие', async () => {
    const problem: JourneyProblem = {
      id: 146,
      content_idx: 1767,
      node_id: 'EQ04',
      statement: 'Реши уравнение 3(x − 2) = 18 и покажи преобразования.',
      topic: { id: 'EQ04', title: 'Линейные уравнения' },
    }
    const task = {
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши полностью на бумаге.',
      photo_required: true,
      help_available: true,
      photo_consent_required: true,
      primary_action: 'Сфотографировать решение',
    } satisfies PhotoTaskStep
    renderJourney(workspaceState(task, 12))
    expect(await screen.findByText(problem.statement)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Ввести ответ' }))
    expect(screen.getByRole('heading', { name: 'Введи свой итоговый ответ' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Позови взрослого на короткий шаг' })).toBeNull()
    expect(screen.getByText(/фото не понадобится/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Отправить фото' }))
    fireEvent.click(screen.getByRole('button', { name: 'Позвать взрослого' }))

    expect(screen.getByText(problem.statement)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Разрешение на проверку фото' })).toBeTruthy()
    const grant = screen.getByRole('button', { name: 'Разрешить проверку фото' }) as HTMLButtonElement
    expect(grant.disabled).toBe(true)
    fireEvent.click(screen.getByRole('checkbox', { name: /я родитель или законный представитель/i }))
    expect(grant.disabled).toBe(false)
    journeyApi.fetchJourney.mockResolvedValue(workspaceState({ ...task, photo_consent_required: false }, 13))
    fireEvent.click(grant)

    await waitFor(() => expect(api.postConsent).toHaveBeenCalledWith(true))
    expect(screen.getByText(problem.statement)).toBeTruthy()
  })

  it('после stale photo upload сохраняет фото и даёт загрузить актуальный маршрут', async () => {
    const problem: JourneyProblem = {
      id: 44,
      content_idx: 1765,
      node_id: 'PC06',
      statement: 'Смешали раствор и воду. Найди новую концентрацию.',
      topic: { id: 'PC06', title: 'Смеси и концентрации' },
    }
    const task = state({
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу полностью и отправь одно фото.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 9)
    const authoritative = state({
      type: 'guided_step',
      title: 'Актуальный разбор сервера',
      problem,
      step: {
        number: 1,
        total: 3,
        instruction: 'Найди массу вещества.',
        prompt: 'Какая масса вещества?',
        format_hint: 'Запиши число и единицу.',
        example: '20 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень.',
      primary_action: 'Проверить шаг',
    }, 11)
    journeyApi.uploadJourneyPhoto.mockRejectedValue(new JourneyApiError(
      409,
      'Маршрут уже изменился. Загрузи актуальный шаг.',
      'stale_revision',
      state({ ...task.next_step }, 10),
    ))

    renderJourney(task)
    const file = new File(['solution'], 'saved-solution.jpg', { type: 'image/jpeg' })
    fireEvent.change(await screen.findByLabelText('Фото всего решения'), { target: { files: [file] } })
    journeyApi.fetchJourney.mockResolvedValue(authoritative)
    fireEvent.click(screen.getByRole('button', { name: 'Отправить решение' }))

    expect(await screen.findByText('saved-solution.jpg')).toBeTruthy()
    fireEvent.click(await screen.findByRole('button', { name: 'Загрузить актуальный маршрут' }))

    expect(await screen.findByRole('heading', { name: 'Актуальный разбор сервера' })).toBeTruthy()
    expect(journeyApi.fetchJourney).toHaveBeenCalledTimes(2)
  })

  it('guided принимает только ответ шага и прямо говорит, что mastery не растёт', async () => {
    const guided = workspaceState({
      type: 'guided_step',
      title: 'Разберём эту же задачу',
      problem: {
        id: 44,
        content_idx: 1765,
        node_id: 'PC06',
        statement: 'Условие той же задачи.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      step: {
        number: 1,
        total: 3,
        instruction: 'Сколько граммов соли было сначала?',
        prompt: 'Найди массу соли.',
        format_hint: 'Запиши массу в граммах.',
        example: '20 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень. Его подтвердит новая самостоятельная задача.',
      primary_action: 'Проверить шаг',
    }, 10)
    journeyApi.submitGuidedAnswer.mockResolvedValue(guided)

    renderJourney(guided)

    expect(await screen.findByText(/Уровень подтвердит следующая самостоятельная задача/)).toBeTruthy()
    expect(screen.getByTestId('guided-contract').textContent).toContain('Найди массу соли.')
    expect(screen.getByTestId('guided-format-hint').textContent).toContain('Запиши массу в граммах.')
    expect(screen.getByTestId('guided-example').textContent).toContain('20 г')
    expect(screen.queryByLabelText('Фото всего решения')).toBeNull()
    fireEvent.change(screen.getByRole('textbox', { name: 'Ответ шага' }), { target: { value: '75' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить шаг' }))

    await waitFor(() => expect(journeyApi.submitGuidedAnswer).toHaveBeenCalledWith(expect.objectContaining({
      revision: 10,
      problem_id: 44,
      step_n: 1,
      answer: '75',
    })))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Проверить шаг' }) as HTMLButtonElement).disabled).toBe(false))
  })

  it('начинает новый диалог AI-помощника при переходе к следующему guided-шагу', async () => {
    const problem: JourneyProblem = {
      id: 44,
      content_idx: 1765,
      node_id: 'PC06',
      statement: 'Условие той же задачи.',
      topic: { id: 'PC06', title: 'Смеси и концентрации' },
    }
    const firstStep = workspaceState({
      type: 'guided_step',
      title: 'Разберём эту же задачу',
      problem,
      step: {
        number: 1,
        total: 3,
        instruction: 'Сколько граммов соли было сначала?',
        prompt: 'Найди массу соли.',
        format_hint: 'Запиши массу в граммах.',
        example: '20 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень.',
      primary_action: 'Проверить шаг',
    }, 10)
    const secondStep = workspaceState({
      type: 'guided_step',
      title: 'Разберём эту же задачу',
      problem,
      step: {
        number: 2,
        total: 3,
        instruction: 'Найди массу воды.',
        prompt: 'Сколько граммов воды было сначала?',
        format_hint: 'Запиши массу в граммах.',
        example: '80 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень.',
      primary_action: 'Проверить шаг',
    }, 11)
    api.sendTutorMessage.mockResolvedValue({
      session_id: 81,
      reply: 'Сначала найди массу соли по процентам.',
      history: [
        { role: 'user', content: 'Что делать на первом шаге?' },
        { role: 'assistant', content: 'Сначала найди массу соли по процентам.' },
      ],
    })
    journeyApi.submitGuidedAnswer.mockResolvedValue(secondStep)

    renderJourney(firstStep)
    fireEvent.click(await screen.findByRole('button', { name: 'Спросить AI-помощника' }))
    const tutorInput = screen.getByRole('textbox', { name: 'Твой вопрос' })
    fireEvent.change(tutorInput, { target: { value: 'Что делать на первом шаге?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить вопрос' }))

    expect(await screen.findByText('Сначала найди массу соли по процентам.')).toBeTruthy()
    expect(api.sendTutorMessage).toHaveBeenCalledWith(44, 'Что делать на первом шаге?', 1765, 1)
    fireEvent.click(screen.getByRole('button', { name: 'Вернуться к задаче' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Ответ шага' }), { target: { value: '20 г' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить шаг' }))

    expect(await screen.findByText('Сколько граммов воды было сначала?')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Спросить AI-помощника' }))
    expect(screen.queryByText('Сначала найди массу соли по процентам.')).toBeNull()
    expect((screen.getByRole('textbox', { name: 'Твой вопрос' }) as HTMLTextAreaElement).value).toBe('')
  })

  it('во время AI-проверки guided сохраняет ответ и не предлагает фото или повторную отправку', async () => {
    const processing = workspaceState({
      type: 'guided_processing',
      title: 'Проверяем этот шаг',
      problem: {
        id: 44,
        content_idx: 1765,
        node_id: 'PC06',
        statement: 'Условие той же задачи.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      step: {
        number: 1,
        total: 3,
        instruction: 'Сколько граммов соли было сначала?',
        prompt: 'Найди массу соли.',
        format_hint: 'Запиши массу в граммах.',
        example: '20 г',
        input_mode: 'text',
      },
      message: 'AI проверяет действие шага.',
      preserved_answer: { value: '75 г' },
      primary_action: 'Проверить статус',
    }, 11)

    renderJourney(processing)

    expect(await screen.findByTestId('guided-processing')).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Твой ответ шага' }) as HTMLInputElement).value).toBe('75 г')
    expect((screen.getByRole('textbox', { name: 'Твой ответ шага' }) as HTMLInputElement).disabled).toBe(true)
    expect(screen.queryByLabelText('Фото всего решения')).toBeNull()
    expect(screen.getByTestId('learning-workspace').querySelectorAll('[data-primary-action]')).toHaveLength(1)
    expect((screen.getByRole('button', { name: 'AI проверяет шаг…' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('transfer снова требует целое решение одним фото и не предлагает guided', async () => {
    renderJourney(state({
      type: 'transfer_task',
      title: 'Проверка переноса',
      mode: 'transfer',
      problem: {
        id: 45,
        content_idx: 331,
        node_id: 'PC06',
        statement: 'Новая задача на испарение воды из раствора.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      instruction: 'Реши задачу полностью на бумаге и отправь одно фото всей страницы.',
      photo_required: true,
      help_available: false,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 13))

    expect(await screen.findByText('Новая задача на испарение воды из раствора.')).toBeTruthy()
    expect(screen.getByLabelText('Фото всего решения')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Не знаю, как решать' })).toBeNull()
  })

  it('очищает выбранное фото при смене ученика даже для той же задачи', async () => {
    const task = state({
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem: {
        id: 45,
        content_idx: 331,
        node_id: 'PC06',
        statement: 'Задача на смесь.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      instruction: 'Реши задачу полностью на бумаге.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 13)
    const view = renderJourney(task)
    const file = new File(['private-solution'], 'student-a.jpg', { type: 'image/jpeg' })
    fireEvent.change(await screen.findByLabelText('Фото всего решения'), { target: { files: [file] } })
    expect(await screen.findByText('student-a.jpg')).toBeTruthy()

    api.useLearningIdentity.mockReturnValue('student-b')
    view.rerenderJourney()

    await waitFor(() => expect(screen.queryByText('student-a.jpg')).toBeNull())
    expect(await screen.findByLabelText('Фото всего решения')).toBeTruthy()
  })

  it('показывает ошибку обновления processing и сохраняет гарантию фото', async () => {
    renderJourney(state({
      type: 'photo_processing',
      title: 'Проверяем ход решения',
      problem: {
        id: 45,
        content_idx: 331,
        node_id: 'PC06',
        statement: 'Задача на смесь.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      message: 'Сверяем каждый шаг.',
      preserved_photo: { name: 'solution.jpg' },
      primary_action: 'Проверить статус',
    }, 14))
    await screen.findByRole('heading', { name: 'Проверяем ход решения' })
    journeyApi.fetchJourney.mockRejectedValue(new Error('Сеть недоступна'))

    fireEvent.click(screen.getByRole('button', { name: 'Проверить статус' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('Не удалось обновить статус')
    expect(alert.textContent).toContain('повторная съёмка не нужна')
    expect(screen.getByText('solution.jpg')).toBeTruthy()
  })

  it('provider recovery не маскирует ошибку и подтверждает сохранённое фото', async () => {
    journeyApi.retryJourneyPhoto.mockResolvedValue(state({
      type: 'photo_feedback',
      problem: {
        id: 45,
        content_idx: 331,
        node_id: 'PC06',
        statement: 'Новая задача.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      verdict: 'correct',
      message: 'Решение подтверждено.',
      primary_action: 'Решить новую задачу',
    }, 15))
    renderJourney(state({
      type: 'photo_recovery',
      problem: {
        id: 45,
        content_idx: 331,
        node_id: 'PC06',
        statement: 'Новая задача.',
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
      },
      reason: 'provider_error',
      message: 'Проверка временно недоступна. Фото сохранено — переснимать его не нужно.',
      preserved_photo: { name: 'solution.jpg' },
      return_stage: 'transfer_task',
      primary_action: 'Повторить проверку',
    }, 14))

    expect((await screen.findByRole('alert')).textContent).toContain('Проверка временно недоступна')
    expect(screen.getByText('solution.jpg')).toBeTruthy()
    expect(screen.getAllByText(/переснимать его не нужно/i)).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Повторить проверку' }))
    await waitFor(() => expect(journeyApi.retryJourneyPhoto).toHaveBeenCalledWith({ revision: 14 }))
  })

  it('передаёт consent взрослому и не отправляет выбранное фото скрыто', async () => {
    const problem: JourneyProblem = {
      id: 51,
      content_idx: 812,
      node_id: 'EQ04',
      statement: 'Реши уравнение и покажи все преобразования.',
      topic: { id: 'EQ04', title: 'Линейные уравнения' },
    }
    const task = state({
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem,
      instruction: 'Реши задачу полностью на бумаге и отправь одно фото всей страницы.',
      photo_required: true,
      help_available: true,
      photo_consent_required: false,
      primary_action: 'Сфотографировать решение',
    }, 20)
    journeyApi.uploadJourneyPhoto.mockRejectedValue(new JourneyApiError(
      403,
      'Нужно разрешение родителя на проверку фото.',
      'consent_required',
    ))

    renderJourney(task)
    const file = new File(['solution'], 'equation.jpg', { type: 'image/jpeg' })
    fireEvent.change(await screen.findByLabelText('Фото всего решения'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить решение' }))

    expect(await screen.findByRole('button', { name: 'Передать взрослому' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Передать взрослому' }))
    expect(screen.getByRole('heading', { name: 'Разрешение на проверку фото' })).toBeTruthy()
    expect(screen.queryByText(problem.statement)).toBeNull()

    const grant = screen.getByRole('button', { name: 'Разрешить проверку фото' })
    expect((grant as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('checkbox', { name: /я родитель или законный представитель/i }))
    journeyApi.fetchJourney.mockResolvedValue(task)
    fireEvent.click(grant)

    await waitFor(() => expect(api.postConsent).toHaveBeenCalledWith(true))
    expect(journeyApi.uploadJourneyPhoto).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('equation.jpg')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Отправить решение' })).toBeTruthy()
  })

  it('показывает ошибку выдачи consent внутри parent handoff', async () => {
    renderJourney(state({
      type: 'independent_task',
      title: 'Реши самостоятельно',
      mode: 'independent',
      problem: {
        id: 52,
        content_idx: 813,
        node_id: 'EQ04',
        statement: 'Реши уравнение.',
        topic: { id: 'EQ04', title: 'Линейные уравнения' },
      },
      instruction: 'Реши задачу на бумаге.',
      photo_required: true,
      help_available: true,
      photo_consent_required: true,
      primary_action: 'Сфотографировать решение',
    }, 21))
    api.postConsent.mockRejectedValue(new Error('Не удалось связаться с сервером'))

    fireEvent.click(await screen.findByRole('button', { name: 'Передать взрослому' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /я родитель или законный представитель/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Разрешить проверку фото' }))

    expect((await screen.findByRole('alert')).textContent).toContain('Не удалось связаться с сервером')
  })

  it('объясняет первое расхождение и предлагает исправить или открыть guided', async () => {
    const problem: JourneyProblem = {
      id: 44,
      content_idx: 1765,
      node_id: 'PC06',
      statement: 'Задача на смесь.',
      topic: { id: 'PC06', title: 'Смеси и концентрации' },
    }
    const guided = state({
      type: 'guided_step',
      title: 'Разберём эту же задачу',
      problem,
      step: {
        number: 1,
        total: 3,
        instruction: 'Найди массу соли.',
        prompt: 'Какая масса соли?',
        format_hint: 'Запиши массу в граммах.',
        example: '20 г',
        input_mode: 'text',
      },
      feedback: null,
      photo_required: false,
      mastery_note: 'Разбор не повышает уровень.',
      primary_action: 'Проверить шаг',
    }, 15)
    journeyApi.continueJourney.mockResolvedValue(guided)
    renderJourney(state({
      type: 'photo_feedback',
      problem,
      verdict: 'incorrect',
      failed_step: 2,
      confirmed_steps: [{ number: 1, label: 'Масса соли найдена верно.' }],
      correction: 'После действия должно получиться 15%.',
      message: 'До этого шага ход решения совпадает.',
      help_available: true,
      mastery: { value: 0.18, threshold: 0.85, reached: false },
      primary_action: 'Исправить решение',
    }, 14))

    expect(await screen.findByText('Масса соли найдена верно.')).toBeTruthy()
    expect(screen.getByText(/Ответ пока не раскрываем/)).toBeTruthy()
    expect(screen.queryByText(/15%/)).toBeNull()
    expect(screen.getByRole('button', { name: 'Исправить решение' })).toBeTruthy()
    const focusSentinel = document.createElement('input')
    focusSentinel.setAttribute('aria-label', 'Legacy practice focus sentinel')
    document.body.append(focusSentinel)
    focusSentinel.focus()
    document.documentElement.scrollTop = 360
    document.body.scrollTop = 140
    fireEvent.click(screen.getByRole('button', { name: 'Разобрать по шагам' }))

    await waitFor(() => expect(journeyApi.continueJourney).toHaveBeenCalledWith({
      revision: 14,
      action: 'review_with_help',
    }))
    expect(await screen.findByRole('heading', { name: 'Разберём эту же задачу' })).toBeTruthy()
    expect(document.documentElement.scrollTop).toBe(360)
    expect(document.body.scrollTop).toBe(140)
    expect(document.activeElement).toBe(focusSentinel)
    focusSentinel.remove()
  })

  it('повторно загружает пустой маршрут', async () => {
    renderJourney(state({
      type: 'route_ready',
      title: 'Твой маршрут готов',
      topics: [],
      primary_action: 'Начать первую тему',
    }, 8))

    fireEvent.click(await screen.findByRole('button', { name: 'Попробовать ещё раз' }))
    await waitFor(() => expect(journeyApi.fetchJourney).toHaveBeenCalledTimes(2))
  })

  it('показывает серверную длительность диагностики без выдуманного тайминга профиля', async () => {
    renderJourney(state({
      type: 'diagnostic_intro',
      title: 'Определим стартовый уровень',
      description: 'Вопросы будут адаптироваться к ответам.',
      estimated_minutes: 6,
      primary_action: 'Начать диагностику',
    }, 3))

    expect(await screen.findByLabelText('6мин: примерное время')).toBeTruthy()
    expect(screen.queryByText(/20 минут/i)).toBeNull()
    expect(screen.queryByText(/≈8/)).toBeNull()
  })

  it('объясняет недостающее подтверждение без противоречивых процентов', async () => {
    renderJourney(state({
      type: 'topic_result',
      title: 'Результат темы',
      topic: {
        id: 'PC06',
        title: 'Смеси и концентрации',
        strand: 'Количественная грамотность',
        goal: 'Решать задачи на смеси.',
        reason: 'Навык нужен для отбора.',
        status: 'next',
      },
      mastery: {
        value: 0.94,
        threshold: 0.85,
        reached: false,
        evidence: {
          correct: 2,
          required_correct: 3,
          remaining_correct: 1,
          total: 2,
          accuracy: 1,
          minimum_accuracy: 0.5,
          probability_reached: true,
          correct_reached: false,
          accuracy_reached: true,
        },
      },
      primary_action: 'Продолжить практику',
    }, 17))

    expect(await screen.findByText('самостоятельных решений')).toBeTruthy()
    expect(screen.queryByText(/навык подтверждён/i)).toBeNull()
    expect(screen.queryByText(/порог .* пройден/i)).toBeNull()
    expect(screen.getByText('2')).toBeTruthy()
    expect(screen.getByText('Осталась 1 новая задача · уверенность 94%')).toBeTruthy()
  })

  it('на финале маршрута сохраняет server-owned действие', async () => {
    renderJourney(state({
      type: 'route_complete',
      title: 'Маршрут завершён',
      description: 'Результаты сохранены.',
      primary_action: 'Посмотреть прогресс',
    }, 30))

    const action = await screen.findByRole('link', { name: 'Посмотреть прогресс' })
    expect(action.getAttribute('href')).toBe('/analytics')
  })
})
