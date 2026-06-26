import { describe, it, expect, vi, afterEach } from 'vitest'
import { fetchWrongTasks, fetchAnalytics, postDiagnose } from '../lib/api'
import type { WrongTask } from '../lib/types'

// Минимальная мок-задача для тестов парсинга.
const MOCK_TASK: WrongTask = {
  id: 'wt-test-01',
  problem_id: 1,
  node_id: 'N01',
  topic_label: 'Тест',
  statement: 'Задача',
  answer: '5',
  primary_micro_skill: null,
  decomp_idx: null,
  steps: [],
  state: 'revisit',
  wrong_answer: '3',
  mastery: 0.3,
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
    expect(result).toHaveLength(1)
    expect(result[0]?.id).toBe('wt-test-01')
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
