// Сжатие изображения перед загрузкой на сервер.
// Длинная сторона масштабируется до ≤ 1568px; конвертируется в JPEG quality=0.8.
// Нормализует EXIF (через createImageBitmap, который декодирует HEIC на Safari 17+).

/** Максимальная длинная сторона результирующего изображения (px). */
const MAX_LONG_EDGE = 1568

// Типобезопасные ссылки на глобальные API (проверяемы через vi.stubGlobal в тестах)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _g = globalThis as any

/**
 * Сжимает файл изображения: масштабирует по длинной стороне и конвертирует в JPEG.
 * Использует OffscreenCanvas (worker-safe). При недоступности API — возвращает исходный файл.
 *
 * @param file — исходный файл (JPEG/PNG/HEIC/WebP)
 * @returns Blob с типом image/jpeg
 */
export async function compressForUpload(file: File): Promise<Blob> {
  // Проверяем доступность API через globalThis, чтобы vi.stubGlobal работало в тестах
  const hasCreateImageBitmap = typeof _g.createImageBitmap === 'function'
  const hasOffscreenCanvas = typeof _g.OffscreenCanvas === 'function'

  if (!hasCreateImageBitmap || !hasOffscreenCanvas) {
    // Fallback на HTMLCanvasElement (основной поток)
    return fallbackCanvas(file)
  }

  try {
    // createImageBitmap декодирует HEIC и применяет EXIF-ориентацию (Safari 17+, Chrome 68+)
    const bitmap = await (_g.createImageBitmap as typeof createImageBitmap)(file)
    const { width, height } = bitmap

    // Вычисляем масштаб по длинной стороне
    const scale = width >= height
      ? Math.min(1, MAX_LONG_EDGE / width)
      : Math.min(1, MAX_LONG_EDGE / height)

    const outW = Math.round(width * scale)
    const outH = Math.round(height * scale)

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-assignment
    const canvas: OffscreenCanvas = new _g.OffscreenCanvas(outW, outH)
    const ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D | null
    if (!ctx) {
      bitmap.close()
      return file
    }

    ctx.drawImage(bitmap as unknown as CanvasImageSource, 0, 0, outW, outH)
    bitmap.close()

    return await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.8 })
  } catch {
    // При любой ошибке декодирования/рисования — возвращаем исходный файл
    return file
  }
}

/**
 * Fallback через обычный HTMLCanvasElement (основной поток, без OffscreenCanvas).
 * Если document или URL.createObjectURL недоступны — сразу возвращает исходный файл.
 */
async function fallbackCanvas(file: File): Promise<Blob> {
  // Проверяем доступность DOM API
  if (
    typeof document === 'undefined' ||
    typeof _g.URL?.createObjectURL !== 'function'
  ) {
    return file
  }

  try {
    const img = await loadImage(file)
    const { naturalWidth: w, naturalHeight: h } = img

    const scale = w >= h
      ? Math.min(1, MAX_LONG_EDGE / w)
      : Math.min(1, MAX_LONG_EDGE / h)

    const canvas = document.createElement('canvas')
    canvas.width = Math.round(w * scale)
    canvas.height = Math.round(h * scale)

    const ctx = canvas.getContext('2d')
    if (!ctx) return file

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))),
        'image/jpeg',
        0.8,
      )
    })
  } catch {
    return file
  }
}

/** Загружает File как HTMLImageElement (нужен URL.createObjectURL). */
function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = (_g.URL as typeof URL).createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = reject
    img.src = url
  })
}
