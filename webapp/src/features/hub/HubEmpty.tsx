import { Link } from 'react-router-dom'

// Empty: всё разобрано — праздничное, ободряющее, одна строка + CTA.
export function HubEmpty() {
  return (
    <div className="clay reveal flex flex-col items-center gap-5 rounded-(--radius-card) px-6 py-12 text-center">
      <div
        className="clay-chip flex size-24 items-center justify-center rounded-full text-5xl"
        style={{ backgroundColor: 'color-mix(in oklab, var(--color-got) 16%, white)' }}
      >
        🎉
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-2xl font-black text-ink">Всё разобрано</h2>
        <p className="max-w-[16rem] text-sm font-semibold text-ink-mute">
          Ни одной незакрытой ошибки. Мозг сегодня прокачан — так держать.
        </p>
      </div>
      <Link
        to="/analytics"
        className="press clay-chip inline-flex min-h-12 items-center rounded-(--radius-button) bg-brand px-6 font-extrabold text-on-brand hover:bg-brand-strong"
      >
        Посмотреть прогресс
      </Link>
    </div>
  )
}
