interface HubErrorProps {
  onRetry: () => void
}

// Error (на уровне компонента): что случилось + как починить, без извинений.
export function HubError({ onRetry }: HubErrorProps) {
  return (
    <div className="flex flex-col items-center gap-5 rounded-(--radius-card) border border-[color-mix(in_oklab,var(--color-revisit)_35%,var(--color-line))] bg-surface px-6 py-12 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--color-revisit)_16%,transparent)]">
        <svg
          viewBox="0 0 24 24"
          className="size-7 text-revisit"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden
        >
          <path d="M12 8v5M12 16.5v.01M3.5 19h17L12 4 3.5 19Z" />
        </svg>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-xl font-extrabold text-ink">
          Срез не загрузился
        </h2>
        <p className="max-w-[16rem] text-sm text-ink-mute">
          Похоже, пропала связь. Проверь интернет и попробуй ещё раз.
        </p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex min-h-11 items-center rounded-(--radius-field) bg-brand px-5 font-semibold text-brand-ink transition-transform duration-200 active:scale-95 hover:bg-brand-strong motion-reduce:transition-none"
      >
        Повторить
      </button>
    </div>
  )
}
