import { useNavigate } from 'react-router-dom'
import type { WrongTask } from '../../lib/types'
import { MathText } from '../../components/MathText'
import { RightIcon } from '../../icons'
import { StateChip } from './StateChip'

interface TaskCardProps { task: WrongTask; index: number }

export function TaskCard({ task, index }: TaskCardProps) {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => navigate(`/drill/${task.id}`)}
      aria-label={`Разобрать: ${task.topic_label}`}
      className="group grid w-full min-w-0 grid-cols-[2.5rem_minmax(0,1fr)] gap-x-3 gap-y-4 border-b border-ink/15 py-6 text-left transition-colors hover:bg-surface/70 md:grid-cols-[3.5rem_minmax(0,1fr)_10rem] md:gap-x-5 md:px-3"
    >
      <span className="font-display text-xl font-semibold leading-none text-brand-deep md:text-2xl" aria-hidden>
        {String(index).padStart(2, '0')}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-title text-ink">{task.topic_label}</h3>
          <StateChip state={task.state} />
        </div>
        <p className="formula-body mt-3 line-clamp-3 max-w-3xl text-[clamp(20px,3vw,28px)] font-semibold leading-tight tracking-[-0.025em] text-ink">
          <MathText text={task.statement} />
        </p>
      </div>
      <div className="col-start-2 flex items-center justify-between gap-4 md:col-start-3 md:row-start-1 md:flex-col md:items-end">
        <p className="text-caption1 text-muted">
          было <span className="font-num font-semibold text-oxide">{task.wrong_answer}</span>
        </p>
        <span className="inline-flex min-h-11 items-center gap-2 rounded-chip bg-brand-soft px-3 text-caption1-medium text-brand-ink transition-colors group-hover:bg-brand">
          Разобрать <RightIcon size={16} />
        </span>
      </div>
    </button>
  )
}
