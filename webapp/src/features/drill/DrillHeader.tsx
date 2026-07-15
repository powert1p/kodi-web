import { useNavigate } from 'react-router-dom'
import { LeftIcon } from '../../icons'

interface DrillHeaderProps { topic: string; current: number; total: number }

export function DrillHeader({ topic, current, total }: DrillHeaderProps) {
  const navigate = useNavigate()
  const value = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0

  return (
    <header className="bg-transparent">
      <div className="mx-auto grid min-h-18 max-w-[90rem] grid-cols-[3rem_minmax(0,1fr)_auto] items-center gap-3 px-4 md:px-8">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label="К моему пути"
          className="grid size-11 place-items-center rounded-full border border-ink/15 bg-surface/70 text-muted transition-colors hover:border-ink/30 hover:text-ink"
        >
          <LeftIcon size={18} />
        </button>
        <div className="h-2 overflow-hidden rounded-full bg-ink/10" role="progressbar" aria-label={`Шаг ${current} из ${total}`} aria-valuemin={0} aria-valuemax={total} aria-valuenow={current}>
          <span className="block h-full rounded-full bg-brand transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${value}%` }} />
        </div>
        <div className="min-w-0 text-right">
          <p className="hidden truncate text-caption2 text-muted sm:block">{topic}</p>
          {total > 0 && <p className="font-display text-caption1-medium text-brand-deep">{String(current).padStart(2, '0')} / {String(total).padStart(2, '0')}</p>}
        </div>
      </div>
    </header>
  )
}
