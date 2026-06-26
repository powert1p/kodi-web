import { describe, it, expect, vi, beforeEach } from 'vitest'
import { compressForUpload } from '../lib/image'

// ——————————————————————————————————
// Мок OffscreenCanvas + createImageBitmap
// ——————————————————————————————————

// Имитируем ImageBitmap с заданными размерами.
function makeMockBitmap(width: number, height: number) {
  return { width, height, close: vi.fn() }
}

// Имитируем OffscreenCanvas, чья convertToBlob возвращает JPEG-блоб.
class MockOffscreenCanvas {
  width: number
  height: number
  private ctx: {
    drawImage: ReturnType<typeof vi.fn>
  }

  constructor(w: number, h: number) {
    this.width = w
    this.height = h
    this.ctx = { drawImage: vi.fn() }
  }

  getContext(_type: string) {
    return this.ctx
  }

  convertToBlob(options?: { type?: string; quality?: number }): Promise<Blob> {
    const type = options?.type ?? 'image/jpeg'
    // Создаём минимальный Blob с нужным MIME-типом
    const blob = new Blob(['fake-jpeg'], { type })
    return Promise.resolve(blob)
  }
}

beforeEach(() => {
  vi.stubGlobal('OffscreenCanvas', MockOffscreenCanvas)
  vi.stubGlobal('createImageBitmap', (_source: unknown) => {
    // Возвращаем «изображение» 3000×2000 (нужно масштабировать до ≤1568px)
    return Promise.resolve(makeMockBitmap(3000, 2000))
  })
})

describe('compressForUpload', () => {
  it('возвращает Blob с типом image/jpeg', async () => {
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    const result = await compressForUpload(file)
    expect(result).toBeInstanceOf(Blob)
    expect(result.type).toBe('image/jpeg')
  })

  it('масштабирует так, что длинная сторона ≤ 1568px', async () => {
    // Проверяем через MockOffscreenCanvas.width/height после вызова.
    // Перехватываем конструктор чтобы проверить dimensions.
    let capturedWidth = 0
    let capturedHeight = 0
    const OrigMock = MockOffscreenCanvas
    vi.stubGlobal('OffscreenCanvas', class extends OrigMock {
      constructor(w: number, h: number) {
        super(w, h)
        capturedWidth = w
        capturedHeight = h
      }
    })

    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    await compressForUpload(file)

    // Длинная сторона должна быть ≤ 1568
    expect(Math.max(capturedWidth, capturedHeight)).toBeLessThanOrEqual(1568)
  })

  it('fallback: если OffscreenCanvas недоступен — возвращает исходный файл', async () => {
    vi.stubGlobal('OffscreenCanvas', undefined)
    vi.stubGlobal('createImageBitmap', undefined)
    // Убираем createObjectURL чтобы fallbackCanvas вернул файл без зависания
    const origURL = globalThis.URL
    vi.stubGlobal('URL', { ...origURL, createObjectURL: undefined })

    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    const result = await compressForUpload(file)
    // Должен вернуть исходный файл (не выбросить, не зависнуть)
    expect(result).toBe(file)
  })
})
