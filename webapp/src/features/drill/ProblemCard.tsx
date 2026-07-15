import { MathText } from '../../components/MathText'

interface ProblemCardProps {
  topic: string
  statement: string
  wrongAnswer: string
}

export function ProblemCard({ topic, statement, wrongAnswer }: ProblemCardProps) {
  return (
    <section className="min-w-0">
      <h1 className="sr-only">{topic}: исходная задача</h1>

      <details className="rounded-control border border-ink/15 bg-surface/60 px-4">
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 text-caption1-medium text-ink marker:hidden">
          <span><span className="text-brand-deep">Исходная задача</span> · {topic}</span>
          <span className="max-w-[46%] shrink-0 text-right">
            <span className="block text-caption2 text-muted">Было</span>
            <span
              className={[
                'number-viewport font-num block text-oxide',
                wrongAnswer.length > 10 ? 'text-caption2' : 'text-caption1-medium',
              ].join(' ')}
              tabIndex={wrongAnswer.length > 10 ? 0 : undefined}
              aria-label={`Предыдущий ответ: ${wrongAnswer}`}
            >
              {wrongAnswer}
            </span>
          </span>
        </summary>
        <div className="math-prose border-t border-ink/10 py-4">
          <p className="formula-body text-2xl font-semibold leading-tight tracking-tight text-ink">
            <MathText text={statement} />
          </p>
        </div>
      </details>

    </section>
  )
}
