import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { MathText } from '../../components/MathText'

interface DiagnosisErrorProps {
  /** Опорный наводящий разбор активного шага (fallback при 503). */
  fallbackHint: string | null
  onRetry: () => void
  onDismiss: () => void
}

// 503-fallback: vision временно недоступен. Без извинений — Кёди всё равно
// поддерживает: даёт наводящий разбор шага + «попробовать ещё».
export function DiagnosisError({ fallbackHint, onRetry, onDismiss }: DiagnosisErrorProps) {
  return (
    <ApCard as="article" padding="m" className="reveal flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <Mascot mood="oops" size="s" className="shrink-0" />
        <div className="flex flex-col gap-0.5 pt-0.5">
          <span className="text-title text-ink">Фото пока не разобрать</span>
          <p className="text-caption2 text-muted">
            Связь с разбором подвисла. Но мы и без фото справимся — вот опора:
          </p>
        </div>
      </div>

      {fallbackHint && (
        <div className="rounded-control bg-paper p-3 text-caption1 text-text">
          <MathText text={fallbackHint} />
        </div>
      )}

      <div className="flex gap-3">
        <ApButton variant="secondary" size="m" onClick={onDismiss} className="flex-1">
          Продолжу сам
        </ApButton>
        <ApButton variant="primary" size="m" onClick={onRetry} className="flex-1">
          Ещё раз фото
        </ApButton>
      </div>
    </ApCard>
  )
}
