import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'

interface FinishedCardProps {
  taskId: string
  answer: string
}

// Лесенка пройдена: лёгкое празднование Кёди + итоговый ответ + чанковая CTA
// «Закрепить →» на /closure/:taskId (большое празднование — уже там).
export function FinishedCard({ taskId, answer }: FinishedCardProps) {
  const navigate = useNavigate()

  return (
    <article className="card-flat reveal flex flex-col items-center gap-3 rounded-(--radius-card) p-5 text-center">
      <Mascot mood="celebrate" size={72} className="bob" />
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-xl font-black text-ink">
          Все шаги пройдены!
        </h2>
        <p className="text-sm font-bold text-ink-mute">
          Итог:{' '}
          <span className="font-num font-extrabold tabular-nums text-got-ink">
            {answer} ₽
          </span>
          . Теперь закрепим — без подсказок.
        </p>
      </div>
      <Button3D
        variant="success"
        size="lg"
        block
        onClick={() => navigate(`/closure/${taskId}`)}
      >
        Закрепить
        <svg
          viewBox="0 0 16 16"
          className="size-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M3 8h9M9 4l4 4-4 4" />
        </svg>
      </Button3D>
    </article>
  )
}
