import { MathText } from '../../components/MathText'

interface ProblemCardProps {
  statement: string
  wrongAnswer: string
}

// Карточка-условие: формулировка через KaTeX (скролл на обёртке внутри MathText),
// плюс эмпатичная плашка «в прошлый раз» с прежним ответом. Плоская и тихая.
export function ProblemCard({ statement, wrongAnswer }: ProblemCardProps) {
  return (
    <article className="card-flat flex flex-col gap-3 rounded-(--radius-card) p-4">
      <span className="text-[0.6rem] font-extrabold uppercase tracking-[0.16em] text-ink-mute">
        Задача
      </span>
      <p className="text-[1.05rem] font-bold leading-snug text-ink">
        <MathText text={statement} />
      </p>

      <div className="flex items-center gap-2 rounded-(--radius-field) bg-surface-soft px-3 py-2">
        <span aria-hidden className="text-sm leading-none">
          ✏️
        </span>
        <span className="text-xs font-bold text-ink-mute">
          В прошлый раз получилось{' '}
          <span className="font-num font-extrabold tabular-nums text-almost-ink">
            {wrongAnswer}
          </span>{' '}
          — разберёмся, где сбилось.
        </span>
      </div>
    </article>
  )
}
