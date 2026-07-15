interface AnalyticsHeaderProps { total: number }

export function AnalyticsHeader({ total }: AnalyticsHeaderProps) {
  return (
    <header>
      <div className="mx-auto grid max-w-[90rem] gap-6 px-5 py-8 md:grid-cols-[minmax(0,1fr)_14rem] md:px-8 md:py-12">
        <div className="flex flex-col justify-center">
          <p className="text-mark text-brand-deep">Прогресс · повторения</p>
          <h1 className="mt-3 max-w-3xl text-[clamp(35px,5vw,56px)] font-bold leading-[1] tracking-[-0.06em] text-ink">Что повторялось в решениях.</h1>
          <p className="mt-4 max-w-2xl text-body text-text">Не оценка темы — только места, которые полезно заметить перед следующим разбором.</p>
        </div>
        <div className="tape-card grid grid-cols-[auto_minmax(0,1fr)] items-end gap-4 px-6 py-5 md:flex md:flex-col md:items-start md:justify-center md:gap-0 md:py-6">
          <p className="font-display text-[clamp(48px,10vw,76px)] font-semibold leading-none text-ink"><span className="bracket-slot" data-state="done">{total}</span></p>
          <p className="pb-2 text-caption1 text-muted md:mt-3 md:pb-0">типов повторений</p>
        </div>
      </div>
    </header>
  )
}
