import { describe, it, expect, vi, afterEach } from 'vitest'
import { startSrez, answerSrez } from '../lib/api'
import { track } from '../lib/telemetry'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function okJson(body: unknown) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response)
}

describe('srez api', () => {
  it('startSrez возвращает список задач', async () => {
    vi.stubGlobal('fetch', vi.fn(() => okJson({ tasks: [{ problem_id: 1, statement: 'x', answer_type: 'number', node_title: 'T', position: 1, total: 12 }] })))
    const tasks = await startSrez()
    expect(tasks).toHaveLength(1)
    expect(tasks[0]?.problem_id).toBe(1)
  })

  it('answerSrez возвращает is_correct', async () => {
    vi.stubGlobal('fetch', vi.fn(() => okJson({ is_correct: false })))
    const res = await answerSrez(1, '5', 1000)
    expect(res.is_correct).toBe(false)
  })
})

describe('telemetry', () => {
  it('отправляет событие с keepalive, чтобы переход по экрану не терял POST', async () => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => 'test-token') })
    const fetchMock = vi.fn(() => okJson({ inserted: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await track('drill_left', { task_id: '3' })

    expect(fetchMock).toHaveBeenCalledWith('/api/trainer/events', expect.objectContaining({
      method: 'POST',
      keepalive: true,
    }))
  })

  it('track глотает сетевую ошибку (fire-and-forget)', async () => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => 'test-token') })
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
    await expect(track('hub_opened')).resolves.toBeUndefined()
  })
})
