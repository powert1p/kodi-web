import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { LongArrowRightIcon } from '../../icons'

interface FinishedCardProps {
  taskId: string
  answer: string
}

// Лесенка пройдена: лёгкое празднование Кёди + итоговый ответ + ApButton
// «Закрепить →» на /closure/:taskId (большое празднование — уже там).
export function FinishedCard({ taskId, answer }: FinishedCardProps) {
  const navigate = useNavigate()

  return (
    <article className="ap-card lift reveal flex flex-col items-center gap-3 p-5 text-center">
      <Mascot mood="celebrate" size="m" className="bob mascot-shadow" />
      <div className="flex flex-col gap-1">
        <h2 className="text-h2 text-ink">Все шаги пройдены!</h2>
        <p className="text-body text-text">
          Итог:{' '}
          <span className="font-num tabular-nums text-success-ink">{answer}</span>. Теперь
          закрепим — без подсказок.
        </p>
      </div>
      <ApButton
        variant="primary"
        size="m"
        full
        onClick={() => navigate(`/closure/${taskId}`)}
      >
        Закрепить
        <LongArrowRightIcon size={18} />
      </ApButton>
    </article>
  )
}
