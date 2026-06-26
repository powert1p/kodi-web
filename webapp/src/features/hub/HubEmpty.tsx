import { Link } from 'react-router-dom'

// Empty: всё разобрано — праздничное, ободряющее, одна строка + CTA.
export function HubEmpty() {
  return (
    <div className="reveal flex flex-col items-center gap-5 rounded-(--radius-card) border border-line/60 bg-surface px-6 py-12 text-center">
      <div className="flex size-20 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--color-got)_18%,transparent)] text-4xl">
        🎉
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-2xl font-extrabold text-ink">
          Всё разобрано
        </h2>
        <p className="max-w-[15rem] text-sm text-ink-mute">
          Ни одной незакрытой ошибки. Мозг прокачан — так держать.
        </p>
      </div>
      <Link
        to="/analytics"
        className="inline-flex min-h-11 items-center rounded-(--radius-field) bg-brand px-5 font-semibold text-brand-ink transition-transform duration-200 active:scale-95 hover:bg-brand-strong motion-reduce:transition-none"
      >
        Посмотреть прогресс
      </Link>
    </div>
  )
}
