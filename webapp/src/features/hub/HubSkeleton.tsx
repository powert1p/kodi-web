// Loading: плоские каркасы — статус-строка + hero с полосой прогресса + плитки задач (shimmer).
export function HubSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Загрузка среза">
      {/* Статус-строка */}
      <div className="flex items-center justify-between">
        <div className="shimmer h-9 w-20 rounded-(--radius-pill) bg-surface-soft" />
        <div className="shimmer h-9 w-24 rounded-(--radius-pill) bg-surface-soft" />
      </div>

      {/* Hero-каркас */}
      <div className="card-flat flex flex-col gap-4 rounded-(--radius-card) p-4">
        <div className="flex items-start gap-3">
          <div className="shimmer size-16 shrink-0 rounded-full bg-surface-soft" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="shimmer h-3 w-24 rounded-(--radius-pill) bg-surface-soft" />
            <div className="shimmer h-6 w-28 rounded-(--radius-field) bg-surface-soft" />
            <div className="shimmer h-3 w-full rounded-(--radius-pill) bg-surface-soft" />
          </div>
        </div>
        <div className="shimmer h-5 w-full rounded-(--radius-pill) bg-surface-soft" />
      </div>

      {/* Плитки-каркасы */}
      {[0, 1, 2].map((i) => (
        <div key={i} className="card-flat flex flex-col gap-3 rounded-(--radius-tile) p-4">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-28 rounded-(--radius-pill) bg-surface-soft" />
            <div className="shimmer h-6 w-20 rounded-(--radius-pill) bg-surface-soft" />
          </div>
          <div className="shimmer h-5 w-full rounded-(--radius-field) bg-surface-soft" />
          <div className="flex items-center justify-between">
            <div className="shimmer h-3 w-24 rounded-(--radius-pill) bg-surface-soft" />
            <div className="shimmer h-12 w-32 rounded-(--radius-button) bg-surface-soft" />
          </div>
        </div>
      ))}
    </div>
  )
}
