import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  advanceLearningLesson,
  answerLearningActivity,
  fetchLearningPath,
  startLearningLesson,
} from '../lib/api'

const JSON_RESPONSE = {
  status: 'active',
  session_id: 1,
  lesson: {},
  progress: { current: 1, total: 6, completed: 0 },
  activity: null,
  feedback: null,
  result: null,
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('learning API', () => {
  it('загружает текущий учебный путь с Bearer token без DEV fallback', async () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn((key: string) => key === 'kodi.jwt' ? 'student-token' : null),
    })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        path: {
          id: 'nish-preparation',
          title: 'Подготовка к НИШ',
          current_block: { id: 'PC06', title: 'Смеси и концентрации', completed_lessons: 0, total_lessons: 1 },
        },
        lesson: { id: 'mixtures-1' },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await fetchLearningPath()

    expect(response.lesson?.id).toBe('mixtures-1')
    expect(response.path.current_block.id).toBe('PC06')
    expect(fetchMock).toHaveBeenCalledWith('/api/learning/path/current', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer student-token' }),
    }))
  })

  it('стартует и продвигает только указанный урок', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => JSON_RESPONSE })
    vi.stubGlobal('fetch', fetchMock)

    await startLearningLesson('mixtures-1')
    await advanceLearningLesson('mixtures-1')

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/learning/start', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ lesson_id: 'mixtures-1' }),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/learning/advance', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ lesson_id: 'mixtures-1' }),
    }))
  })

  it('передаёт стабильный client_attempt_id и не отправляет content_idx', async () => {
    let body = ''
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      body = String(init.body)
      return Promise.resolve({ ok: true, json: async () => JSON_RESPONSE })
    }))

    await answerLearningActivity({
      lessonId: 'mixtures-1',
      activityId: 'guided-substance',
      activityIndex: 1,
      answer: '20',
      clientAttemptId: 'attempt-fixed-123',
      responseTimeMs: 2800,
    })

    expect(JSON.parse(body)).toEqual({
      lesson_id: 'mixtures-1',
      activity_id: 'guided-substance',
      activity_index: 1,
      answer: '20',
      client_attempt_id: 'attempt-fixed-123',
      response_time_ms: 2800,
    })
    expect(body).not.toContain('content_idx')
  })

  it('при stale activity принимает authoritative state из 409', async () => {
    const authoritative = {
      ...JSON_RESPONSE,
      progress: { current: 3, total: 6, completed: 2 },
      activity: { id: 'guided-total' },
    }
    const errorResponse = {
      ok: false,
      status: 409,
      clone() { return this },
      json: async () => ({
        detail: { code: 'stale_activity', state: authoritative },
      }),
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(errorResponse))

    const result = await answerLearningActivity({
      lessonId: 'mixtures-1',
      activityId: 'guided-substance',
      activityIndex: 1,
      answer: '250',
      clientAttemptId: 'stale-attempt',
    })

    expect(result.activity?.id).toBe('guided-total')
    expect(result.progress.completed).toBe(2)
  })
})
