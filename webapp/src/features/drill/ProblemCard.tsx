import { MathText } from '../../components/MathText'

interface ProblemCardProps {
  statement: string
  wrongAnswer: string
}

// Карточка-условие (AiPlus ap-card): формулировка через KaTeX + эмпатичная плашка
// «в прошлый раз» с прежним ответом (мягкий тон, без карающего красного).
export function ProblemCard({ statement, wrongAnswer }: ProblemCardProps) {
  return (
    <article className="ap-card flex flex-col gap-3 p-4">
      <span className="text-caption2-medium uppercase tracking-[0.12em] text-text-secondary">
        Задача
      </span>
      <p className="text-body text-text-primary">
        <MathText text={statement} />
      </p>

      <div className="flex items-center gap-2 rounded-lg bg-bg-secondary px-3 py-2">
        <span aria-hidden className="text-sm leading-none">
          ✏️
        </span>
        <span className="text-caption2 text-text-secondary">
          В прошлый раз получилось{' '}
          <span className="font-num tabular-nums text-text-brand">{wrongAnswer}</span>{' '}
          — разберёмся, где сбилось.
        </span>
      </div>
    </article>
  )
}
