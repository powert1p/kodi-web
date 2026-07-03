import { MathText } from '../../components/MathText'
import { ApCard } from '../../components/ApCard'

interface ProblemCardProps {
  statement: string
  wrongAnswer: string
}

// Карточка-условие: формулировка через KaTeX (учебный текст — canon §1: минимум
// 18px) + эмпатичная плашка «в прошлый раз» с прежним ответом (мягкий тон).
export function ProblemCard({ statement, wrongAnswer }: ProblemCardProps) {
  return (
    <ApCard as="article" padding="m" className="flex flex-col gap-3">
      <span className="text-caption2-medium uppercase tracking-[0.12em] text-muted">
        Задача
      </span>
      <p className="text-study text-ink">
        <MathText text={statement} />
      </p>

      <div className="flex items-center gap-2 rounded-control bg-paper px-3 py-2">
        <span aria-hidden className="text-sm leading-none">
          ✏️
        </span>
        <span className="text-caption2 text-muted">
          В прошлый раз получилось{' '}
          <span className="font-num tabular-nums text-brand">{wrongAnswer}</span>{' '}
          — разберёмся, где сбилось.
        </span>
      </div>
    </ApCard>
  )
}
