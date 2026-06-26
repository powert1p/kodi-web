// Loading: глиняные каркасы — hero-панель + плитки задач с shimmer.
export function HubSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-busy="true" aria-label="Загрузка среза">
      {/* Hero-каркас */}
      <div className="clay flex items-center gap-4 rounded-(--radius-card) p-5">
        <div className="flex flex-1 flex-col gap-2.5">
          <div className="shimmer h-3 w-24 rounded-(--radius-pill) bg-surface-muted" />
          <div className="shimmer h-6 w-full rounded-(--radius-field) bg-surface-muted" />
          <div className="shimmer h-3 w-3/4 rounded-(--radius-pill) bg-surface-muted" />
        </div>
        <div className="shimmer size-[116px] shrink-0 rounded-full bg-surface-muted" />
      </div>

      {/* Плитки-каркасы */}
      {[0, 1, 2].map((i) => (
        <div key={i} className="clay flex flex-col gap-3 rounded-(--radius-tile) p-4">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-28 rounded-(--radius-pill) bg-surface-muted" />
            <div className="shimmer h-6 w-20 rounded-(--radius-pill) bg-surface-muted" />
          </div>
          <div className="shimmer h-5 w-full rounded-(--radius-field) bg-surface-muted" />
          <div className="shimmer h-5 w-2/3 rounded-(--radius-field) bg-surface-muted" />
        </div>
      ))}
    </div>
  )
}
