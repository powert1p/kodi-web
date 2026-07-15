import { useRef } from 'react'
import type { ChangeEvent } from 'react'
import { ApButton } from '../../components/ApButton'
import { CameraUploadIcon } from '../../icons'
import { HintBanner } from './HintBanner'
import { track } from '../../lib/telemetry'
import type { StepVerdict } from '../../lib/types'
import type { StepSubmitStatus } from './useStepSubmitFlow'

interface StepSubmitPanelProps {
  stepN: number
  status: StepSubmitStatus
  verdict: StepVerdict | null
  onPhoto: (file: File) => void
  /** Сброс flow перед повторным фото (не needsConsent-ветка — её берёт DrillPage/ConsentCard). */
  onRetry: () => void
}

// Панель сдачи режима «По тетради»: вместо текстового поля активной ступени —
// кнопка «Сфотать шаг N». match НЕ рендерит баннер здесь — DrillPage сразу
// засчитывает ступень верной и сбрасывает flow, панель перемонтируется на
// следующий шаг (или пропадает, если это была последняя ступень).
export function StepSubmitPanel({ stepN, status, verdict, onPhoto, onRetry }: StepSubmitPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // ВАЖНО: onRetry() вызывается ЗДЕСЬ (когда файл уже выбран), а не перед
  // открытием пикера — иначе reset() перемонтирует панель на idle-ветку ДО
  // того, как нативный диалог выбора файла успеет отдать file, скрытый
  // <input> уже отключён от DOM и событие change никуда не долетает (был
  // живой баг: «Сфотать заново» молча ничего не делал).
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Телеметрия ретрая после unsure — на фактическом повторном фото (файл
      // реально выбран), а не на приходе вердикта: до этого момента пользователь
      // мог и не повторить попытку.
      if (verdict?.verdict === 'unsure') void track('step_retry_after_unsure')
      onRetry()
      onPhoto(file)
    }
    // сброс — чтобы повторный выбор того же файла триггерил change (как PhotoCapture)
    e.target.value = ''
  }

  const hiddenInput = (
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
  )

  const openPicker = () => inputRef.current?.click()

  if (status === 'idle') {
    return (
      <div className="flex flex-col gap-2">
        {hiddenInput}
        <ApButton variant="primary" size="m" full onClick={openPicker}>
          <CameraUploadIcon size={20} />
          Сфотать шаг {stepN}
        </ApButton>
      </div>
    )
  }

  if (status === 'uploading' || status === 'submitting') {
    return (
      <div
        className="reveal border-l-4 border-blue bg-surface p-4"
        aria-busy="true"
        aria-label="Кёди смотрит фото шага"
      >
        <p className="text-mark text-blue-deep">Проверяем фото</p>
        <span className="mt-2 block text-title text-ink">Сверяем только этот шаг…</span>
      </div>
    )
  }

  if (status === 'result' && verdict) {
    // match: ступень уже уходит в solved (мост в DrillPage) — панель молчит.
    if (verdict.verdict === 'match') return null

    const isUnsure = verdict.verdict === 'unsure'
    const text = isUnsure
      ? 'Не разглядел — сфотай ещё раз, только этот шаг крупнее'
      : (verdict.hint ?? 'Проверь этот шаг ещё раз')

    return (
      <div className="flex flex-col gap-3">
        <HintBanner text={text} variant="hint" />
        {hiddenInput}
        <ApButton variant="secondary" size="m" full onClick={openPicker}>
          <CameraUploadIcon size={20} />
          Сфотать заново
        </ApButton>
      </div>
    )
  }

  // error, не needsConsent (тот случай перехватывает ConsentCard в DrillPage) —
  // 503/сетевая ошибка: поддерживающий fallback голосом Кёди + повтор.
  return (
    <div className="flex flex-col gap-3">
      <HintBanner text="Не получилось посмотреть фото — соединение подвело. Попробуй ещё раз." variant="hint" />
      {hiddenInput}
      <ApButton variant="secondary" size="m" full onClick={openPicker}>
        <CameraUploadIcon size={20} />
        Сфотать заново
      </ApButton>
    </div>
  )
}
