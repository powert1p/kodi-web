import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { ApiError } from '../lib/api'
import type { StepVerdict } from '../lib/types'

// Мокаем postStepSubmit — тест логики хука, не сети.
// ⚠️ useStepSubmit() внутри api.ts вызывает postStepSubmit через локальную
// ссылку модуля (self-reference), которую spread `{ ...actual }` НЕ перехватывает —
// поэтому useStepSubmit тоже переопределяем поверх мокнутого postStepSubmit.
vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  const { useMutation } = await import('@tanstack/react-query')
  const postStepSubmit = vi.fn()
  return {
    ...actual,
    postStepSubmit,
    useStepSubmit: () => useMutation({ mutationFn: postStepSubmit }),
  }
})

import { postStepSubmit } from '../lib/api'
import { useStepSubmitFlow } from '../features/drill/useStepSubmitFlow'

// compressForUpload() без стаба зависает в jsdom (Image.onload не срабатывает
// на фейковых байтах) — стабим OffscreenCanvas/createImageBitmap как в image.test.ts.
beforeEach(() => {
  vi.stubGlobal('OffscreenCanvas', class {
    convertToBlob() {
      return Promise.resolve(new Blob(['fake-jpeg'], { type: 'image/jpeg' }))
    }
    getContext() {
      return { drawImage: vi.fn() }
    }
  })
  vi.stubGlobal('createImageBitmap', () => Promise.resolve({ width: 100, height: 100, close: vi.fn() }))
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient()
  return createElement(QueryClientProvider, { client }, children)
}

const FILE = new File(['x'], 'step.jpg', { type: 'image/jpeg' })

describe('useStepSubmitFlow', () => {
  it('успешный вердикт mismatch с hint пробрасывается в результат', async () => {
    const verdict: StepVerdict = { verdict: 'mismatch', hint: 'Проверь базу процента', confidence: 0.6, step_n: 1 }
    vi.mocked(postStepSubmit).mockResolvedValue(verdict)

    const { result } = renderHook(() => useStepSubmitFlow(), { wrapper })

    await act(async () => {
      await result.current.start(FILE, { decomp_idx: 0, step_n: 1 })
    })

    expect(result.current.status).toBe('result')
    expect(result.current.verdict?.hint).toBe('Проверь базу процента')
    expect(result.current.needsConsent).toBe(false)
  })

  it('вердикт unsure — это успешный результат, а не ошибка (status=result)', async () => {
    const verdict: StepVerdict = { verdict: 'unsure', hint: null, confidence: 0.5, step_n: 1 }
    vi.mocked(postStepSubmit).mockResolvedValue(verdict)

    const { result } = renderHook(() => useStepSubmitFlow(), { wrapper })

    await act(async () => {
      await result.current.start(FILE, { decomp_idx: 0, step_n: 1 })
    })

    expect(result.current.status).toBe('result')
    expect(result.current.verdict?.verdict).toBe('unsure')
    expect(result.current.is503).toBe(false)
    expect(result.current.needsConsent).toBe(false)
  })

  it('403 consent_required переводит needsConsent=true', async () => {
    vi.mocked(postStepSubmit).mockRejectedValue(new ApiError(403, 'consent_required'))

    const { result } = renderHook(() => useStepSubmitFlow(), { wrapper })

    await act(async () => {
      await result.current.start(FILE, { decomp_idx: 0, step_n: 1 })
    })

    expect(result.current.needsConsent).toBe(true)
    expect(result.current.status).toBe('error')
  })

  it('503 переводит is503=true', async () => {
    vi.mocked(postStepSubmit).mockRejectedValue(new ApiError(503, 'unavailable'))

    const { result } = renderHook(() => useStepSubmitFlow(), { wrapper })

    await act(async () => {
      await result.current.start(FILE, { decomp_idx: 0, step_n: 1 })
    })

    expect(result.current.is503).toBe(true)
    expect(result.current.status).toBe('error')
  })
})
