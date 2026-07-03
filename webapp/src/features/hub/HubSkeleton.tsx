// Loading: плоские каркасы — статус-строка + hero с полосой + плитки (shimmer).
export function HubSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Загрузка среза">
      {/* Статус-строка */}
      <div className="flex items-center justify-between">
        <div className="shimmer h-9 w-20 rounded-full bg-paper" />
        <div className="shimmer h-9 w-24 rounded-full bg-paper" />
      </div>

      {/* Hero-каркас */}
      <div className="ap-card flex flex-col gap-4 p-4">
        <div className="flex items-start gap-3">
          <div className="shimmer size-16 shrink-0 rounded-full bg-paper" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="shimmer h-3 w-24 rounded-chip bg-paper" />
            <div className="shimmer h-6 w-28 rounded-chip bg-paper" />
            <div className="shimmer h-3 w-full rounded-chip bg-paper" />
          </div>
        </div>
        <div className="shimmer h-2 w-full rounded-full bg-paper" />
      </div>

      {/* Плитки-каркасы */}
      {[0, 1, 2].map((i) => (
        <div key={i} className="ap-card flex flex-col gap-3 p-4">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-28 rounded-chip bg-paper" />
            <div className="shimmer h-6 w-20 rounded-chip bg-paper" />
          </div>
          <div className="shimmer h-5 w-full rounded-chip bg-paper" />
          <div className="flex items-center justify-between">
            <div className="shimmer h-3 w-24 rounded-chip bg-paper" />
            <div className="shimmer h-10 w-28 rounded-control bg-paper" />
          </div>
        </div>
      ))}
    </div>
  )
}
