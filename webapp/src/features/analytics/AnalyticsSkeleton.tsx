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
        <div className="shimmer size-14 shrink-0 rounded-full bg-paper" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="shimmer h-3 w-28 rounded-chip bg-paper" />
          <div className="shimmer h-6 w-40 rounded-chip bg-paper" />
          <div className="shimmer h-3 w-full rounded-chip bg-paper" />
        </div>
      </div>

      {/* Каркасы полос — убывающая длина */}
      {[100, 78, 60, 44, 30].map((w, i) => (
        <div key={i} className="ap-card flex flex-col gap-2 p-4">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-36 rounded-chip bg-paper" />
            <div className="shimmer h-4 w-8 rounded-chip bg-paper" />
          </div>
          <div
            className="shimmer h-2 rounded-full bg-paper"
            style={{ width: `${w}%` }}
          />
        </div>
      ))}
    </div>
  )
}
