import { useEffect, useRef } from 'react'
import { MathText } from '../../components/MathText'

interface SrezQuestionCardProps {
  topic: string
  statement: string
  answerType: string | null
  value: string
  disabled: boolean
  onChange: (value: string) => void
}

export function SrezQuestionCard({ topic, statement, answerType, value, disabled, onChange }: SrezQuestionCardProps) {
  const questionRef = useRef<HTMLHeadingElement>(null)
  const firstQuestionRef = useRef(true)

  useEffect(() => {
    if (firstQuestionRef.current) {
      firstQuestionRef.current = false
      return
    }
    questionRef.current?.focus()
  }, [statement])

  return (
    <section aria-labelledby="srez-question" className="tape-stage min-w-0 px-5 py-6 md:px-9 md:py-9">
      <p className="relative text-mark text-brand-deep">Вопрос · {topic}</p>
      <div className="math-prose relative mt-4 pb-2 md:mt-6">
        <h1 ref={questionRef} tabIndex={-1} id="srez-question" className="formula-body max-w-5xl text-[clamp(30px,5vw,52px)] font-bold leading-[1.08] tracking-[-0.045em] text-ink">
          <MathText text={statement} />
        </h1>
      </div>
      <label htmlFor="srez-answer" className="relative mt-5 block text-caption1-medium text-muted md:mt-7">Твой ответ</label>
      <div className="answer-panel math-viewport relative mt-3 pb-3">
        <div className="font-display inline-flex min-w-max items-center gap-[0.22em] text-[clamp(34px,9vw,62px)] font-semibold leading-none tracking-[-0.055em]">
          <span className="text-muted">Ответ</span>
          <span className="text-muted">=</span>
          <span className="bracket-slot" data-state="active">
            <input
              id="srez-answer"
              inputMode={answerInputMode(answerType)}
              autoComplete="off"
              placeholder="?"
              aria-label="Введите ответ"
              value={value}
              disabled={disabled}
              maxLength={64}
              onChange={(event) => onChange(event.target.value)}
              className="equation-input"
            />
          </span>
        </div>
      </div>
    </section>
  )
}

function answerInputMode(answerType: string | null): 'numeric' | 'decimal' | 'text' {
  if (answerType === 'number' || answerType === 'integer') return 'numeric'
  if (answerType === 'decimal') return 'decimal'
  return 'text'
}
