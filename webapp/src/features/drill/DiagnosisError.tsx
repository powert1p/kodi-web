import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'
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
    <article className="card-flat reveal flex flex-col gap-3 rounded-(--radius-card) p-4">
      <div className="flex items-start gap-2.5">
        <Mascot mood="oops" size={44} className="shrink-0" />
        <div className="flex flex-col gap-0.5 pt-0.5">
          <span className="font-display text-base font-extrabold text-ink">
            Фото пока не разобрать
          </span>
          <p className="text-xs font-bold text-ink-mute">
            Связь с разбором подвисла. Но мы и без фото справимся — вот опора:
          </p>
        </div>
      </div>

      {fallbackHint && (
        <div className="rounded-(--radius-field) bg-surface-soft p-3 text-sm font-bold leading-snug text-ink">
          <MathText text={fallbackHint} />
        </div>
      )}

      <div className="flex gap-2.5">
        <Button3D variant="secondary" size="lg" onClick={onDismiss} className="flex-1">
          Продолжу сам
        </Button3D>
        <Button3D variant="primary" size="lg" onClick={onRetry} className="flex-1">
          Ещё раз фото
        </Button3D>
      </div>
    </article>
  )
}
