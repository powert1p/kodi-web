// Loading: каркас шапки + descending shimmer-полосы (как у будущих ErrorBar).
export function AnalyticsSkeleton() {
  return (
    <div
      className="flex flex-col gap-4"
      aria-busy="true"
      aria-label="Загрузка прогресса"
    >
      {/* Каркас шапки */}
      <div className="card-flat flex items-start gap-3 rounded-(--radius-card) p-4">
        <div className="shimmer size-14 shrink-0 rounded-full bg-surface-soft" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="shimmer h-3 w-28 rounded-(--radius-pill) bg-surface-soft" />
          <div className="shimmer h-6 w-40 rounded-(--radius-field) bg-surface-soft" />
          <div className="shimmer h-3 w-full rounded-(--radius-pill) bg-surface-soft" />
        </div>
      </div>

      {/* Каркасы полос — убывающая длина */}
      {[100, 78, 60, 44, 30].map((w, i) => (
        <div
          key={i}
          className="card-flat flex flex-col gap-2 rounded-(--radius-card) p-3.5"
        >
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-36 rounded-(--radius-pill) bg-surface-soft" />
            <div className="shimmer h-4 w-8 rounded-(--radius-pill) bg-surface-soft" />
          </div>
          <div
            className="shimmer h-3 rounded-(--radius-pill) bg-surface-soft"
            style={{ width: `${w}%` }}
          />
        </div>
      ))}
    </div>
  )
}
