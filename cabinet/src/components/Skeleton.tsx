// Скелетоны для состояния загрузки хаба: shimmer-плейсхолдеры.
export function HubSkeleton() {
  return (
    <div className="space-y-4">
      <div className="shimmer h-[150px] rounded-[20px] bg-line/60" />
      <div className="shimmer h-9 w-2/3 rounded-pill bg-line/60" />
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="shimmer h-[120px] rounded-[16px] bg-line/50"
        />
      ))}
    </div>
  );
}
