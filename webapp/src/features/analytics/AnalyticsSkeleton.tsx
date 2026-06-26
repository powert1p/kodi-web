// Loading: каркас шапки + descending shimmer-полосы (как у будущих ErrorBar).
export function AnalyticsSkeleton() {
  return (
    <div
      className="flex flex-col gap-4"
      aria-busy="true"
      aria-label="Загрузка прогресса"
    >
      {/* Каркас шапки */}
      <div className="ap-card flex items-start gap-3 p-4">
        <div className="shimmer size-14 shrink-0 rounded-full bg-bg-secondary" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="shimmer h-3 w-28 rounded-sm bg-bg-secondary" />
          <div className="shimmer h-6 w-40 rounded-sm bg-bg-secondary" />
          <div className="shimmer h-3 w-full rounded-sm bg-bg-secondary" />
        </div>
      </div>

      {/* Каркасы полос — убывающая длина */}
      {[100, 78, 60, 44, 30].map((w, i) => (
        <div key={i} className="ap-card flex flex-col gap-2 p-3.5">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-36 rounded-sm bg-bg-secondary" />
            <div className="shimmer h-4 w-8 rounded-sm bg-bg-secondary" />
          </div>
          <div
            className="shimmer h-2 rounded-xs bg-bg-secondary"
            style={{ width: `${w}%` }}
          />
        </div>
      ))}
    </div>
  )
}
