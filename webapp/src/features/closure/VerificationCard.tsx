import { useState, type FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'

interface VerificationCardProps {
  statement: string
  wrong: boolean
  networkError: boolean
  attempts: number
  checking: boolean
  onCheck: (value: string) => void
  onResume: () => void
}

export function VerificationCard({
  statement,
  wrong,
  networkError,
  attempts,
  checking,
  onCheck,
  onResume,
}: VerificationCardProps) {
  const [value, setValue] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!value.trim() || checking) return
    onCheck(value)
  }

  function change(next: string) {
    setValue(next)
    if (wrong || networkError) onResume()
  }

  return (
    <article className="tape-stage px-5 py-6 md:px-9 md:py-10">
      <div className="relative flex items-center justify-between gap-3">
        <p className="text-mark text-brand-deep">Новая задача</p>
        <span className="text-caption1 text-muted">без подсказок</span>
      </div>
      <div className="math-prose relative mt-4 pb-2 md:mt-6">
        <h2 className="formula-body max-w-4xl text-[clamp(30px,5vw,50px)] font-bold leading-[1.08] tracking-[-0.045em] text-ink">
          <MathText text={statement} />
        </h2>
      </div>

      <form onSubmit={submit} className="relative mt-5 md:mt-8">
        <label htmlFor="closure-answer" className="text-caption1-medium text-muted">Твой ответ</label>
        <div className="answer-panel math-viewport mt-3 pb-3">
          <div className="font-display inline-flex min-w-max items-center gap-[0.22em] text-[clamp(34px,9vw,62px)] font-semibold leading-none tracking-[-0.055em]">
            <span className="text-muted">Ответ</span>
            <span className="text-muted">=</span>
            <span className="bracket-slot" data-state={wrong ? 'wrong' : 'active'}>
              <input
                id="closure-answer"
                inputMode="text"
                value={value}
                onChange={(event) => change(event.target.value)}
                disabled={checking}
                placeholder="?"
                aria-label="Введите ответ контрольной"
                aria-invalid={wrong || undefined}
                autoComplete="off"
                maxLength={64}
                className="equation-input"
              />
            </span>
          </div>
        </div>
        {(wrong || networkError) && <div className="relative mt-4" aria-live="polite">
          {wrong && (
            <div className="reveal rounded-control border border-oxide/20 border-l-4 border-l-oxide bg-oxide-soft px-4 py-3 text-text">
              <p className="text-caption1-medium"><span className="font-semibold text-oxide">Пока не сошлось.</span> {attempts >= 2 ? 'Перечитай условие и проверь каждый шаг ещё раз.' : 'Проверь числа и попробуй снова. Ответ не раскрываем.'}</p>
            </div>
          )}
          {networkError && (
            <div className="reveal rounded-control border border-brand/20 border-l-4 border-l-brand bg-brand-soft/45 px-4 py-3 text-text" role="alert">
              <p className="text-caption1-medium"><span className="font-semibold text-brand-deep">Нет связи.</span> Ответ сохранён — нажми «Проверить решение» ещё раз.</p>
            </div>
          )}
        </div>}
        <ApButton type="submit" size="l" className="mt-5 w-full sm:w-auto sm:min-w-56 md:mt-6" loading={checking} disabled={!value.trim() || checking}>
          Проверить решение
        </ApButton>
      </form>
    </article>
  )
}
