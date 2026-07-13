import { MathText } from '../../components/MathText'
import { ApCard } from '../../components/ApCard'

interface ProblemCardProps {
  statement: string
  wrongAnswer: string
}

// Карточка-условие (ведущая, крафт-lift-sm): формулировка через KaTeX (учебный текст
// ≥18px, формулы-чипы) + эмпатичная плашка «в прошлый раз» с прежним ответом (мягкий тон).
export function ProblemCard({ statement, wrongAnswer }: ProblemCardProps) {
  return (
    <ApCard as="article" padding="m" className="lift-sm flex flex-col gap-3">
      <span className="font-display text-caption2-medium uppercase tracking-[0.12em] text-brand-ink">
        Задача
      </span>
      <p className="formula-body text-study text-ink">
        <MathText text={statement} />
      </p>

      <div className="flex items-center gap-2 rounded-control bg-attn-soft px-3 py-2">
        <span aria-hidden className="text-attn-ink">
          <PenIcon />
        </span>
        <span className="text-caption1 text-attn-ink">
          В прошлый раз получилось{' '}
          <span className="font-num tabular-nums text-ink">{wrongAnswer}</span> — разберёмся, где
          сбилось.
        </span>
      </div>
    </ApCard>
  )
}

// Перо-иконка (крафт-акцент вместо эмодзи ✏️ — §Anti-references «эмодзи вместо иконок»).
function PenIcon() {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20l4-1L19 8a2 2 0 0 0-3-3L5 16z" />
      <path d="M14 7l3 3" />
    </svg>
  )
}
