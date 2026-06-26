import { useNavigate, useParams } from 'react-router-dom'
import { Button3D } from '../../components/Button3D'

interface PlaceholderPageProps {
  title: string
  note: string
}

// Плоский плейсхолдер для маршрутов, которые строятся в следующих задачах.
export function PlaceholderPage({ title, note }: PlaceholderPageProps) {
  const { taskId } = useParams()
  const navigate = useNavigate()

  return (
    <div className="reveal flex flex-col gap-4 pt-1">
      <Button3D
        variant="secondary"
        size="md"
        onClick={() => navigate('/')}
        className="self-start"
      >
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
          <path d="M13 8H4M7 4 3 8l4 4" />
        </svg>
        К срезу
      </Button3D>

      <div className="card-flat flex flex-col gap-3 rounded-(--radius-card) px-5 py-10">
        <h1 className="font-display text-2xl font-black text-ink">{title}</h1>
        <p className="text-sm font-semibold text-ink-mute">{note}</p>
        {taskId && (
          <span className="font-num w-fit rounded-(--radius-field) bg-surface-soft px-2.5 py-1 text-xs font-bold tabular-nums text-ink">
            task: {taskId}
          </span>
        )}
      </div>
    </div>
  )
}
