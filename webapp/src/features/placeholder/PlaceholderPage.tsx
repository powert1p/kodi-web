import { Link, useParams } from 'react-router-dom'

interface PlaceholderPageProps {
  title: string
  note: string
}

// Минимальный плейсхолдер для маршрутов, которые строятся в следующих задачах.
export function PlaceholderPage({ title, note }: PlaceholderPageProps) {
  const { taskId } = useParams()

  return (
    <div className="reveal flex flex-col gap-4 pt-2">
      <Link
        to="/"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-semibold text-ink-mute transition-colors hover:text-ink"
      >
        <svg
          viewBox="0 0 16 16"
          className="size-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M13 8H4M7 4 3 8l4 4" />
        </svg>
        К срезу
      </Link>

      <div className="flex flex-col gap-3 rounded-(--radius-card) border border-line/60 bg-surface px-5 py-10">
        <h1 className="font-display text-2xl font-extrabold text-ink">{title}</h1>
        <p className="text-sm text-ink-mute">{note}</p>
        {taskId && (
          <span className="font-num w-fit rounded-(--radius-field) bg-raised px-2.5 py-1 text-xs text-ink-soft">
            task: {taskId}
          </span>
        )}
      </div>
    </div>
  )
}
