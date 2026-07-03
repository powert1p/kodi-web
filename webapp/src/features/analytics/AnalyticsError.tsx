import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'
import { RestartIcon } from '../../icons'

interface AnalyticsErrorProps {
  onRetry: () => void
}

// Error (на уровне компонента): что случилось + как починить. Без красного, без извинений.
export function AnalyticsError({ onRetry }: AnalyticsErrorProps) {
  return (
    <ApCard padding="l" className="reveal flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="oops" size="l" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h3 text-ink">Прогресс не загрузился</h2>
        <p className="max-w-[16rem] text-caption1 text-muted">
          Похоже, пропала связь. Проверь интернет и попробуй ещё раз.
        </p>
      </div>
      <ApButton variant="primary" size="m" onClick={onRetry}>
        <RestartIcon size={18} />
        Повторить
      </ApButton>
    </ApCard>
  )
}
