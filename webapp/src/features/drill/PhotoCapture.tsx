import { useRef } from 'react'
import type { ChangeEvent } from 'react'
import { Button3D } from '../../components/Button3D'

interface PhotoCaptureProps {
  /** Выбран файл фото решения. */
  onPhoto: (file: File) => void
  disabled?: boolean
}

// Headline-действие: чанковая 3D-кнопка «Сфотографировать решение».
// Скрытый <input capture=environment> открывает камеру; выбранный файл уходит
// в compressForUpload → диагноз. Подпись объясняет, зачем фото.
export function PhotoCapture({ onPhoto, disabled = false }: PhotoCaptureProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onPhoto(file)
    // сброс — чтобы повторный выбор того же файла триггерил change
    e.target.value = ''
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleChange}
        className="sr-only"
        aria-hidden
        tabIndex={-1}
      />
      <Button3D
        variant="primary"
        size="lg"
        block
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        <svg
          viewBox="0 0 24 24"
          className="size-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M3 8h3l1.5-2h9L18 8h3v11H3z" />
          <circle cx="12" cy="13" r="3.5" />
        </svg>
        Сфотографировать решение
      </Button3D>
      <p className="px-1 text-center text-xs font-bold text-ink-mute">
        Застрял? Покажи Кёди свою запись — найдём, где сбилось.
      </p>
    </div>
  )
}
