import { Link, useParams } from 'react-router-dom'

interface PlaceholderPageProps {
  title: string
  note: string
}

// Минимальный глиняный плейсхолдер для маршрутов, которые строятся в следующих задачах.
export function PlaceholderPage({ title, note }: PlaceholderPageProps) {
  const { taskId } = useParams()

  return (
    <div className="reveal flex flex-col gap-4 pt-1">
      <Link
        to="/"
        className="press clay-chip inline-flex w-fit items-center gap-1.5 rounded-(--radius-pill) bg-surface px-3 py-2 text-sm font-extrabold text-ink-soft hover:text-brand"
      >
        <svg
          viewBox="0 0 16 16"
          className="size-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M13 8H4M7 4 3 8l4 4" />
        </svg>
        К срезу
      </Link>

      <div className="clay flex flex-col gap-3 rounded-(--radius-card) px-5 py-10">
        <h1 className="font-display text-2xl font-black text-ink">{title}</h1>
        <p className="text-sm font-semibold text-ink-mute">{note}</p>
        {taskId && (
          <span className="font-num w-fit rounded-(--radius-field) bg-surface-muted px-2.5 py-1 text-xs font-bold text-ink-soft tabular-nums">
            task: {taskId}
          </span>
        )}
      </div>
    </div>
  )
}
