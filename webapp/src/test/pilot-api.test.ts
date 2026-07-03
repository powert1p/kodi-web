import { describe, it, expect, vi, afterEach } from 'vitest'
import { startSrez, answerSrez } from '../lib/api'
import { track } from '../lib/telemetry'

afterEach(() => vi.restoreAllMocks())

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
  it('track глотает сетевую ошибку (fire-and-forget)', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
    await expect(track('hub_opened')).resolves.toBeUndefined()
  })
})
