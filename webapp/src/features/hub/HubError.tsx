interface HubErrorProps {
  onRetry: () => void
}

// Error (на уровне компонента): что случилось + как починить, без извинений и без карающего тона.
export function HubError({ onRetry }: HubErrorProps) {
  return (
    <div className="clay reveal flex flex-col items-center gap-5 rounded-(--radius-card) px-6 py-12 text-center">
      <div
        className="clay-chip flex size-20 items-center justify-center rounded-full"
        style={{ backgroundColor: 'color-mix(in oklab, var(--color-revisit) 14%, white)' }}
      >
        <svg
          viewBox="0 0 24 24"
          className="size-9 text-revisit"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M21 12a9 9 0 1 1-3-6.7M21 4v5h-5" />
        </svg>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-xl font-black text-ink">Срез не загрузился</h2>
        <p className="max-w-[16rem] text-sm font-semibold text-ink-mute">
          Похоже, пропала связь. Проверь интернет и попробуй ещё раз.
        </p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="press clay-chip inline-flex min-h-12 items-center rounded-(--radius-button) bg-brand px-6 font-extrabold text-on-brand hover:bg-brand-strong"
      >
        Повторить
      </button>
    </div>
  )
}
