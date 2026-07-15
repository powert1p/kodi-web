export function AnalyticsSkeleton() {
  return (
    <div aria-busy="true" aria-label="Загрузка прогресса" className="min-h-dvh bg-paper">
      <div className="px-5 py-10 md:px-8">
        <div className="mx-auto max-w-[90rem]"><div className="shimmer h-3 w-40 rounded-chip bg-paper-2" /><div className="shimmer mt-6 h-12 w-4/5 max-w-3xl rounded-control bg-paper-2" /><div className="shimmer mt-4 h-6 w-3/5 max-w-2xl rounded-control bg-paper-2" /></div>
      </div>
      <div className="mx-auto max-w-[90rem] px-5 py-12 md:px-8">
        {[0, 1, 2, 3].map((item) => <div key={item} className="grid grid-cols-[3rem_1fr_4rem] gap-4 border-b border-ink/10 py-7"><div className="shimmer h-8 rounded-full bg-brand-soft" /><div className="shimmer h-6 rounded-control bg-paper-2" /><div className="shimmer h-10 rounded-control bg-paper-2" /></div>)}
      </div>
    </div>
  )
}
