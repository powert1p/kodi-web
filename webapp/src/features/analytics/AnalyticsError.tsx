import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { RestartIcon } from '../../icons'

interface AnalyticsErrorProps {
  onRetry: () => void
}

// Error (на уровне компонента): что случилось + как починить. Без красного, без извинений.
export function AnalyticsError({ onRetry }: AnalyticsErrorProps) {
  return (
    <div className="ap-card reveal flex flex-col items-center gap-5 px-6 py-12 text-center">
      <Mascot mood="oops" size={88} />
      <div className="flex flex-col gap-1.5">
        <h2 className="text-h3 text-text-primary">Прогресс не загрузился</h2>
        <p className="max-w-[16rem] text-caption1 text-text-secondary">
          Похоже, пропала связь. Проверь интернет и попробуй ещё раз.
        </p>
      </div>
      <ApButton variant="filled" size="m" onClick={onRetry}>
        <RestartIcon size={18} />
        Повторить
      </ApButton>
    </div>
  )
}
