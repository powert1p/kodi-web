import { useRef } from 'react'
import type { ChangeEvent } from 'react'
import { ApButton } from '../../components/ApButton'
import { CameraUploadIcon } from '../../icons'

interface PhotoCaptureProps {
  /** Выбран файл фото решения. */
  onPhoto: (file: File) => void
  disabled?: boolean
}

// Headline-действие: ApButton «Сфотографировать решение» (бренд-заливка, full-width).
// Скрытый <input capture=environment> открывает камеру; файл уходит в compressForUpload
// → диагноз. Иконка cloud_upload из набора AiPlus.
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
      <ApButton
        variant="primary"
        size="m"
        full
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        <CameraUploadIcon size={20} />
        Сфотографировать решение
      </ApButton>
      <p className="px-1 text-center text-caption2 text-muted">
        Застрял? Покажи Кёди свою запись — найдём, где сбилось.
      </p>
    </div>
  )
}
