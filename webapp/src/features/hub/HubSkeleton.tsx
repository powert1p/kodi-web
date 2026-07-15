export function HubSkeleton() {
  return (
    <div aria-busy="true" aria-label="Загрузка задач на разбор" className="min-h-dvh bg-paper">
      <section className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-[90rem] items-center gap-7 px-5 py-8 md:px-8 lg:grid-cols-[minmax(15rem,0.72fr)_minmax(26rem,1.15fr)_minmax(11rem,0.42fr)] lg:gap-12">
        <div>
          <div className="shimmer h-3 w-36 rounded-chip bg-paper-2" />
          <div className="shimmer mt-5 h-11 w-full rounded-control bg-paper-2" />
          <div className="shimmer mt-3 h-11 w-4/5 rounded-control bg-paper-2" />
          <div className="shimmer mt-5 h-5 w-3/4 rounded-chip bg-paper-2" />
        </div>
        <div className="tape-card tape-card--notched px-6 py-7 pl-14">
          <div className="shimmer h-3 w-32 rounded-chip bg-paper-2" />
          <div className="shimmer mt-8 h-14 w-4/5 rounded-control bg-paper-2" />
          <div className="shimmer mt-7 h-5 w-2/3 rounded-chip bg-paper-2" />
          <div className="shimmer mt-6 h-14 w-full rounded-control bg-brand-soft" />
        </div>
        <div className="hidden lg:block">
          <div className="shimmer h-44 w-full rounded-card bg-sage-soft" />
        </div>
      </section>
      <section className="mx-auto max-w-[90rem] px-5 py-12 md:px-8">
        <div className="shimmer h-10 w-72 rounded-control bg-paper-2" />
        {[0, 1].map((item) => (
          <div key={item} className="grid grid-cols-[3rem_minmax(0,1fr)] gap-4 border-b border-ink/10 py-6 md:grid-cols-[4rem_minmax(0,1fr)_10rem]">
            <div className="shimmer h-8 rounded-full bg-brand-soft" />
            <div><div className="shimmer h-5 w-1/3 rounded-chip bg-paper-2" /><div className="shimmer mt-3 h-7 w-full rounded-control bg-paper-2" /></div>
          </div>
        ))}
      </section>
    </div>
  )
}
