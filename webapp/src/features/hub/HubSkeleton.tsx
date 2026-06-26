// Loading: каркас карточек с shimmer. Та же геометрия, что у TaskCard.
export function HubSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-label="Загрузка среза">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="flex items-stretch gap-3 overflow-hidden rounded-(--radius-card) border border-line/60 bg-surface"
        >
          <div className="shimmer w-[4.25rem] shrink-0 self-stretch bg-raised" />
          <div className="flex flex-1 flex-col gap-3 py-4 pr-4">
            <div className="shimmer h-3 w-24 rounded bg-raised" />
            <div className="shimmer h-4 w-full rounded bg-raised" />
            <div className="shimmer h-4 w-3/4 rounded bg-raised" />
          </div>
        </div>
      ))}
    </div>
  )
}
