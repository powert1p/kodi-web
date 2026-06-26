// Loading: плоские каркасы AiPlus — статус-строка + hero с полосой + плитки (shimmer).
export function HubSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Загрузка среза">
      {/* Статус-строка */}
      <div className="flex items-center justify-between">
        <div className="shimmer h-9 w-20 rounded-full bg-bg-secondary" />
        <div className="shimmer h-9 w-24 rounded-full bg-bg-secondary" />
      </div>

      {/* Hero-каркас */}
      <div className="ap-card flex flex-col gap-4 p-4">
        <div className="flex items-start gap-3">
          <div className="shimmer size-16 shrink-0 rounded-full bg-bg-secondary" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="shimmer h-3 w-24 rounded-sm bg-bg-secondary" />
            <div className="shimmer h-6 w-28 rounded-sm bg-bg-secondary" />
            <div className="shimmer h-3 w-full rounded-sm bg-bg-secondary" />
          </div>
        </div>
        <div className="shimmer h-2 w-full rounded-xs bg-bg-secondary" />
      </div>

      {/* Плитки-каркасы */}
      {[0, 1, 2].map((i) => (
        <div key={i} className="ap-card flex flex-col gap-3 p-4">
          <div className="flex items-center justify-between">
            <div className="shimmer h-4 w-28 rounded-sm bg-bg-secondary" />
            <div className="shimmer h-6 w-20 rounded-sm bg-bg-secondary" />
          </div>
          <div className="shimmer h-5 w-full rounded-sm bg-bg-secondary" />
          <div className="flex items-center justify-between">
            <div className="shimmer h-3 w-24 rounded-sm bg-bg-secondary" />
            <div className="shimmer h-10 w-28 rounded-lg bg-bg-secondary" />
          </div>
        </div>
      ))}
    </div>
  )
}
