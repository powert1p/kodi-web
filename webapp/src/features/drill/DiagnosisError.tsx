import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { MathText } from '../../components/MathText'

interface DiagnosisErrorProps {
  /** Опорный наводящий разбор активного шага (fallback при 503). */
  fallbackHint: string | null
  onRetry: () => void
  onDismiss: () => void
}

// 503-fallback: vision временно недоступен. Без извинений и красного —
// Кёди всё равно поддерживает: даёт наводящий разбор шага + «попробовать ещё».
export function DiagnosisError({ fallbackHint, onRetry, onDismiss }: DiagnosisErrorProps) {
  return (
    <article className="ap-card reveal flex flex-col gap-3 p-4">
      <div className="flex items-start gap-2.5">
        <Mascot mood="oops" size={44} className="shrink-0" />
        <div className="flex flex-col gap-0.5 pt-0.5">
          <span className="text-title text-text-primary">Фото пока не разобрать</span>
          <p className="text-caption2 text-text-secondary">
            Связь с разбором подвисла. Но мы и без фото справимся — вот опора:
          </p>
        </div>
      </div>

      {fallbackHint && (
        <div className="rounded-lg bg-bg-tertiary p-3 text-caption1 text-text-primary">
          <MathText text={fallbackHint} />
        </div>
      )}

      <div className="flex gap-2.5">
        <ApButton variant="outlined" size="m" onClick={onDismiss} className="flex-1">
          Продолжу сам
        </ApButton>
        <ApButton variant="filled" size="m" onClick={onRetry} className="flex-1">
          Ещё раз фото
        </ApButton>
      </div>
    </article>
  )
}
