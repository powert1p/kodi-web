import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  fetchWrongTasks,
  fetchAnalytics,
  postDiagnose,
  asAnalyticsData,
  fetchProblemTopics,
  startVerification,
  answerVerification,
  sendTutorMessage,
} from '../lib/api'
import type { WrongTask } from '../lib/types'

// ——————————————————————————————————
// Вспомогательная функция для теста селектора useWrongTask.
// Хук нельзя вызвать вне рендера — проверяем логику select-коллбэка напрямую.
// ——————————————————————————————————
function selectById(tasks: WrongTask[], id: string): WrongTask | undefined {
  return tasks.find((t) => t.id === id)
}

// Минимальная мок-задача для тестов парсинга.
const MOCK_TASK: WrongTask = {
  id: 'wt-test-01',
  problem_id: 1,
  node_id: 'N01',
  topic_label: 'Тест',
  statement: 'Задача',
  answer: '5',
  primary_micro_skill: null,
  primary_micro_skill_label: null,
  decomp_idx: null,
  steps: [],
  state: 'revisit',
  wrong_answer: '3',
  mastery: 0.3,
  theory_ru: null,
}

afterEach(() => {
  vi.restoreAllMocks()
})

// ——————————————————————————————————
// fetchWrongTasks
// ——————————————————————————————————

describe('fetchWrongTasks', () => {
  it('парсит {tasks} из успешного ответа', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tasks: [MOCK_TASK] }),
    }))

    const result = await fetchWrongTasks()
    expect(result.tasks).toHaveLength(1)
    expect(result.tasks[0]?.id).toBe('wt-test-01')
  })

  it('прокидывает has_activity=false у новичка (пустой список)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tasks: [], has_activity: false }),
    }))

    const result = await fetchWrongTasks()
    expect(result.tasks).toHaveLength(0)
    expect(result.has_activity).toBe(false)
  })

  it('прокидывает has_activity=true у ветерана', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tasks: [], has_activity: true }),
    }))

    const result = await fetchWrongTasks()
    expect(result.has_activity).toBe(true)
  })

  it('бросает ошибку при не-2xx ответе', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
    }))

    await expect(fetchWrongTasks()).rejects.toThrow('401')
  })

  it('при NetworkError (rejected fetch) — пробрасывает ошибку', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(fetchWrongTasks()).rejects.toThrow('Failed to fetch')
  })
})

// ——————————————————————————————————
// fetchAnalytics
// ——————————————————————————————————

describe('fetchAnalytics', () => {
  it('возвращает объект из /api/trainer/analytics', async () => {
    const mockData = { total: 10, mastered: 3 }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    }))

    const result = await fetchAnalytics()
    expect(result).toEqual(mockData)
  })
})

// ——————————————————————————————————
// postDiagnose — multipart body
// ——————————————————————————————————

describe('postDiagnose', () => {
  it('отправляет multipart с полями problem_id и photo', async () => {
    const mockDiagnosis = {
      transcription: 'Ответ',
      failed_step: 1,
      cause_text: 'Арифметическая ошибка',
      level: 2,
      micro_skill: 'addition',
      confidence: 0.9,
      image_ref: 'img123',
    }

    let capturedBody: FormData | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      capturedBody = init.body as FormData
      return Promise.resolve({
        ok: true,
        json: async () => mockDiagnosis,
      })
    }))

    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    const result = await postDiagnose({ problem_id: 42, photo: file })

    expect(result.failed_step).toBe(1)
    // Проверяем что тело — FormData с нужными полями
    expect(capturedBody).toBeInstanceOf(FormData)
    expect((capturedBody as unknown as FormData).get('problem_id')).toBe('42')
    expect((capturedBody as unknown as FormData).get('photo')).toBe(file)
  })

  it('пробрасывает ошибку при не-2xx ответе', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
    }))

    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    await expect(postDiagnose({ problem_id: 1, photo: file })).rejects.toThrow('422')
  })
})

// ——————————————————————————————————
// Селектор useWrongTask: логика find по id
// ——————————————————————————————————

describe('useWrongTask selector (selectById)', () => {
  const tasks: WrongTask[] = [
    { ...MOCK_TASK, id: 'wt-aaa' },
    { ...MOCK_TASK, id: 'wt-bbb' },
  ]

  it('находит задачу по существующему id', () => {
    const result = selectById(tasks, 'wt-aaa')
    expect(result?.id).toBe('wt-aaa')
  })

  it('возвращает undefined для несуществующего id', () => {
    const result = selectById(tasks, 'wt-zzz')
    expect(result).toBeUndefined()
  })

  it('в пустом массиве всегда undefined', () => {
    const result = selectById([], 'wt-aaa')
    expect(result).toBeUndefined()
  })
})

// ——————————————————————————————————
// asAnalyticsData (my_top контракт)
// ——————————————————————————————————

describe('asAnalyticsData (my_top контракт)', () => {
  it('нормализует {my_top} в AnalyticsData', () => {
    const raw = { my_top: [{ micro_skill: 'pc', label_ru: 'Проценты', error_count: 3, last_cause_text: null, node_id: 'PC02' }] }
    const result = asAnalyticsData(raw)
    expect(result?.my_top).toHaveLength(1)
    expect(result?.my_top[0]?.micro_skill).toBe('pc')
  })
  it('возвращает null если my_top отсутствует', () => {
    expect(asAnalyticsData({ foo: 1 })).toBeNull()
  })
})

describe('fetchProblemTopics', () => {
  it('парсит {topics}', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ topics: [{ topic_id: '6.PC', strand: 'PC', name_ru: 'Проценты', error_count: 3, top_micro_skills: ['pc'], nodes_mastery_avg: 0.4, closure_progress: 0.5 }] }),
    }))
    const result = await fetchProblemTopics()
    expect(result).toHaveLength(1)
    expect(result[0]?.topic_id).toBe('6.PC')
  })
})

describe('verification', () => {
  it('startVerification постит problem_id', async () => {
    let body: string | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_u: string, init: RequestInit) => {
      body = init.body as string
      return Promise.resolve({ ok: true, json: async () => ({ problem_id: 2, node_id: 'VF01', topic_label: 'x', statement: 'q', micro_skill: 'vf', xp: 30 }) })
    }))
    const res = await startVerification(1, 'vf')
    expect(res.problem_id).toBe(2)
    expect(JSON.parse(body as unknown as string).problem_id).toBe(1)
  })
  it('answerVerification возвращает correct', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ correct: true }) }))
    const res = await answerVerification(2, '20', 'vf')
    expect(res.correct).toBe(true)
  })
})

describe('sendTutorMessage', () => {
  it('возвращает reply + history', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 1, reply: 'подумай', history: [{ role: 'user', content: 'hi' }, { role: 'assistant', content: 'подумай' }] }),
    }))
    const res = await sendTutorMessage(1, 'hi')
    expect(res.reply).toBe('подумай')
    expect(res.history).toHaveLength(2)
  })
})
