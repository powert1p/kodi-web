import { useNavigate } from 'react-router-dom'
import { LeftIcon } from '../icons'
import { BrandMark } from './BrandMark'

interface FocusTopbarProps { label?: string; meta?: string }

export function FocusTopbar({ label = 'К моему пути', meta }: FocusTopbarProps) {
  const navigate = useNavigate()
  return (
    <header className="bg-transparent">
      <div className="mx-auto grid min-h-18 max-w-[90rem] grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-4 md:px-8">
        <BrandMark className="hidden sm:inline-flex" />
        <button
          type="button"
          onClick={() => navigate('/')}
          className="inline-flex min-h-11 w-max items-center gap-2 rounded-chip border border-ink/15 bg-surface/70 px-4 text-caption1-medium text-muted transition-colors hover:border-ink/30 hover:text-ink sm:col-start-2"
        >
          <LeftIcon size={17} />
          {label}
        </button>
        {meta && <span className="font-display rounded-chip bg-brand-soft px-3 py-2 text-caption2-medium text-brand-ink">{meta}</span>}
      </div>
    </header>
  )
}
