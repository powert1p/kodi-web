import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'

interface AnalyticsErrorProps {
  onRetry: () => void
}

// Error (на уровне компонента): что случилось + как починить. Без красного, без извинений.
export function AnalyticsError({ onRetry }: AnalyticsErrorProps) {
  return (
    <div className="card-flat reveal flex flex-col items-center gap-5 rounded-(--radius-card) px-6 py-12 text-center">
      <Mascot mood="oops" size={88} />
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-xl font-black text-ink">
          Прогресс не загрузился
        </h2>
        <p className="max-w-[16rem] text-sm font-semibold text-ink-mute">
          Похоже, пропала связь. Проверь интернет и попробуй ещё раз.
        </p>
      </div>
      <Button3D variant="primary" size="lg" onClick={onRetry}>
        <svg
          viewBox="0 0 24 24"
          className="size-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M21 12a9 9 0 1 1-3-6.7M21 4v5h-5" />
        </svg>
        Повторить
      </Button3D>
    </div>
  )
}
