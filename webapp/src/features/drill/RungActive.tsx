import { useEffect, useRef, useState, type FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'
import { HintBanner } from './HintBanner'
import type { Rung } from '../../lib/ladder'
import { STEP3_OPTIONS } from './mock'
import { skillLabel } from './microSkillLabel'
import { track } from '../../lib/telemetry'

interface RungActiveProps {
  rung: Rung
  index: number
  hint: boolean
  hintText?: string | null
  showReveal: boolean
  justInserted: boolean
  focusOnMount: boolean
  photoMode?: boolean
  checking?: boolean
  onSubmit: (value: string) => void | Promise<void>
}

export function RungActive({
  rung,
  index,
  hint,
  hintText,
  showReveal,
  justInserted,
  focusOnMount,
  photoMode = false,
  checking = false,
  onSubmit,
}: RungActiveProps) {
  const [value, setValue] = useState('')
  const isChoose = rung.answerKind === 'choose'
  const label = skillLabel(rung.microSkill)
  const stepWord = rung.kind === 'easier' ? 'Разминка' : `Шаг ${index}`
  const isSocraticHint = hint && !(rung.kind === 'easier' && justInserted) && !photoMode
  const prevSocraticHintRef = useRef(false)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (focusOnMount) headingRef.current?.focus()
  }, [focusOnMount, rung.key])

  useEffect(() => {
    if (isSocraticHint && !prevSocraticHintRef.current) void track('hint_shown')
    prevSocraticHintRef.current = isSocraticHint
  }, [isSocraticHint])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!value.trim()) return
    void onSubmit(value)
  }

  return (
    <article className="tape-stage reveal px-5 py-6 md:px-8 md:py-8" aria-current="step">
      <div className="relative flex items-center justify-between gap-3">
        <span className="text-mark text-brand-deep">{label ?? stepWord}</span>
        <span className="font-display text-caption1 text-muted">{stepWord.toLowerCase()}</span>
      </div>

      <h2 ref={headingRef} tabIndex={-1} className="formula-body relative mt-5 max-w-4xl text-[clamp(27px,5vw,44px)] font-semibold leading-[1.08] tracking-[-0.045em] text-ink md:mt-6">
        <MathText text={rung.instruction} />
      </h2>

      {!photoMode && (
        isChoose ? (
          <div className="relative mt-8 grid grid-cols-2 gap-3">
            {STEP3_OPTIONS.map((option) => (
              <ApButton key={option} variant="secondary" size="l" disabled={checking} onClick={() => void onSubmit(option)} className="capitalize">
                {option} цена
              </ApButton>
            ))}
          </div>
        ) : (
          <form onSubmit={submit} className="relative mt-6 md:mt-8">
            <label className="block text-caption1-medium text-muted" htmlFor={`answer-${rung.key}`}>
              Твой следующий шаг
            </label>
            <div className="answer-panel math-viewport mt-3 pb-3">
              <div className="font-display inline-flex min-w-max items-center gap-[0.22em] text-[clamp(34px,9vw,62px)] font-semibold leading-none tracking-[-0.055em]">
                <span className="text-muted">Ответ</span>
                <span className="text-muted">=</span>
                <span className="bracket-slot" data-state={hint ? 'wrong' : 'active'}>
                  <input
                    id={`answer-${rung.key}`}
                    inputMode="text"
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    placeholder="?"
                    aria-label="Введите ответ"
                    aria-invalid={hint || undefined}
                    autoComplete="off"
                    maxLength={64}
                    className="equation-input"
                  />
                </span>
              </div>
            </div>
            <ApButton type="submit" size="l" full disabled={!value.trim() || checking} className="mt-4 sm:w-auto sm:min-w-56 md:mt-5">
              {checking ? 'Проверяем…' : 'Проверить шаг'}
            </ApButton>
          </form>
        )
      )}

      <div className="relative mt-5" aria-live="polite">
        {hint && rung.kind === 'easier' && justInserted && (
          <HintBanner text="Сначала маленький разогрев — потом вернёмся к основному шагу." variant="easier" />
        )}
        {isSocraticHint && <HintBanner text={hintText ?? socraticHint(rung)} variant="hint" />}
        {showReveal && rung.reveal && (
          <details className="mt-4 rounded-control border border-brand/25 border-l-4 border-l-brand bg-brand-soft/50 p-4 text-ink">
            <summary className="flex min-h-11 cursor-pointer items-center text-caption1-medium text-brand-ink">Разобрать этот шаг</summary>
            <p className="formula-body mt-3 text-study text-text"><MathText text={rung.reveal} /></p>
          </details>
        )}
      </div>
    </article>
  )
}

function socraticHint(rung: Rung): string {
  const bySkill: Record<string, string> = {
    'Процент от числа': 'Чтобы найти процент от числа, умножь число на долю. Во что превращается $15\\%$?',
    'Прибавить процент': 'Рост означает прибавку. Что нужно прибавить к исходной цене?',
    'База процента': 'После подорожания цена уже изменилась. От какой суммы теперь считаем процент?',
    'Вычесть процент': 'Сначала найди $10\\%$ от текущей цены, затем вычти эту часть.',
  }
  return bySkill[rung.microSkill] ?? 'Посмотри на предыдущий шаг: какое число оттуда нужно использовать здесь?'
}
