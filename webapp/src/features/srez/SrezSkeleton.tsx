export function SrezSkeleton() {
  return (
    <div className="w-full" aria-busy="true" aria-label="Готовим срез">
      <div className="tape-stage min-h-96 p-7">
        <div className="shimmer h-3 w-28 rounded-chip bg-paper-2" />
        <div className="shimmer mt-8 h-10 w-full rounded-control bg-paper-2" />
        <div className="shimmer mt-3 h-10 w-4/5 rounded-control bg-paper-2" />
        <div className="shimmer mt-12 h-20 w-3/5 rounded-control bg-sage-soft" />
      </div>
      <div className="shimmer mt-4 h-14 w-full max-w-56 bg-brand-soft" />
    </div>
  )
}
