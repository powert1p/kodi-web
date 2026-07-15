import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAnalytics, useProblemTopics } from '../lib/api'
import { useMe } from '../features/auth/useMe'
import { setToken } from '../lib/auth'

function tokenFor(studentId: string): string {
  return `header.${btoa(JSON.stringify({ sub: studentId }))}.signature`
}

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children)
  }
}

function makeStorageMock(): Storage {
  let store: Record<string, string> = {}
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = value },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (index) => Object.keys(store)[index] ?? null,
  } as Storage
}

describe('student query isolation', () => {
  let requestCount: Record<string, number>

  beforeEach(() => {
    vi.stubGlobal('localStorage', makeStorageMock())
    requestCount = {}
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      requestCount[url] = (requestCount[url] ?? 0) + 1
      const revision = requestCount[url]

      if (url.endsWith('/trainer/analytics')) {
        return Promise.resolve({ ok: true, json: async () => ({ student: revision }) })
      }
      if (url.endsWith('/trainer/problem-topics')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ topics: [{ topic_id: `student-${revision}` }] }),
        })
      }
      if (url.endsWith('/auth/me')) {
        return Promise.resolve({ ok: true, json: async () => ({ id: revision }) })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('не отдаёт аналитику, темы и профиль прошлого ученика после смены JWT', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = wrapperFor(client)
    setToken(tokenFor('student-a'))

    const hook = renderHook(
      () => ({ analytics: useAnalytics(), topics: useProblemTopics(), me: useMe() }),
      { wrapper },
    )
    await waitFor(() => expect((hook.result.current.analytics.data as { student?: number })?.student).toBe(1))
    await waitFor(() => expect(hook.result.current.topics.data?.[0]?.topic_id).toBe('student-1'))
    await waitFor(() => expect(hook.result.current.me.data?.id).toBe(1))

    const nextToken = tokenFor('student-b')
    act(() => {
      localStorage.setItem('kodi.jwt', nextToken)
      window.dispatchEvent(new StorageEvent('storage', { key: 'kodi.jwt', newValue: nextToken }))
    })

    await waitFor(() => expect((hook.result.current.analytics.data as { student?: number })?.student).toBe(2))
    await waitFor(() => expect(hook.result.current.topics.data?.[0]?.topic_id).toBe('student-2'))
    await waitFor(() => expect(hook.result.current.me.data?.id).toBe(2))
    expect(requestCount['/api/trainer/analytics']).toBe(2)
    expect(requestCount['/api/trainer/problem-topics']).toBe(2)
    expect(requestCount['/api/auth/me']).toBe(2)

    hook.unmount()
    client.clear()
  })
})
