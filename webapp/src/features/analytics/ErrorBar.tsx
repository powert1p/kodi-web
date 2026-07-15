import type { CSSProperties } from 'react'
import type { ErrorType } from '../../lib/types'

interface ErrorBarProps { item: ErrorType; rank: number; delay: number }

export function ErrorBar({ item, rank, delay }: ErrorBarProps) {
  const focus = rank === 1
  return (
    <article
      className={[
        'reveal grid min-w-0 grid-cols-[3rem_minmax(0,1fr)_auto] gap-4 border-b border-ink/15 py-6 md:grid-cols-[4.5rem_minmax(0,1fr)_9rem] md:gap-6 md:px-3 md:py-7',
        focus ? 'rounded-control border border-l-4 border-ink/10 border-l-brand bg-surface px-3 shadow-lift-sm md:px-5' : '',
      ].join(' ')}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <span className="font-display text-2xl font-semibold leading-none text-brand-deep md:text-3xl" aria-hidden>{String(rank).padStart(2, '0')}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className={focus ? 'text-h3 text-ink' : 'text-title text-ink'}>{item.label}</h2>
          {focus && <span className="rounded-chip bg-brand-soft px-2 py-1 text-caption2-medium text-brand-ink">в фокусе</span>}
        </div>
        {item.last_cause && <p className="mt-2 max-w-2xl text-caption1 text-muted">Последнее наблюдение: {item.last_cause}</p>}
      </div>
      <div className="text-right">
        <span className="font-display text-4xl font-semibold leading-none text-ink">{item.count}</span>
        <p className="mt-1 text-caption2 text-muted">случаев</p>
      </div>
    </article>
  )
}
