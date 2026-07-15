interface SrezHeaderProps { current: number; total: number }

export function SrezHeader({ current, total }: SrezHeaderProps) {
  return (
    <section className="mb-4" aria-label={`Вопрос ${current} из ${total}`}>
      <div className="mb-3 flex items-center justify-between gap-4">
        <div>
          <p className="text-mark text-brand-deep">Мини-срез</p>
          <p className="mt-1 text-caption2 text-muted">Один вопрос за раз · без подсказок</p>
        </div>
        <p className="font-display rounded-chip bg-brand-soft px-3 py-2 text-caption1-medium text-brand-ink">
          {String(current).padStart(2, '0')} / {String(total).padStart(2, '0')}
        </p>
      </div>
      <ol className="flex items-center gap-1" role="progressbar" aria-label={`Вопрос ${current} из ${total}`} aria-valuemin={1} aria-valuemax={total} aria-valuenow={current}>
        {Array.from({ length: total }, (_, index) => {
          const number = index + 1
          return (
            <li
              key={number}
              className={[
                'h-2 min-w-1 flex-1 rounded-full',
                number < current ? 'bg-success' : number === current ? 'bg-brand ring-2 ring-brand-soft' : 'bg-ink/15',
              ].join(' ')}
            >
              <span className="sr-only">Вопрос {number}: {number < current ? 'пройден' : number === current ? 'текущий' : 'впереди'}</span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
