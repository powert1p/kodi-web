import { useState } from 'react'
import type { FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { ApTag } from '../../components/ApTag'
import { Mascot } from '../../components/Mascot'
import type { VerificationProblem } from './mock'

interface VerificationCardProps {
  problem: VerificationProblem
  /** Промах: показать мягкий ретрай-баннер (НИКОГДА красный). */
  wrong: boolean
  /** Сколько раз промахнулся — мягко меняет тон строки. */
  attempts: number
  /** Проверить ответ. */
  onCheck: (value: string) => void
  /** Ввод изменился после промаха — вернуть в solving. */
  onResume: () => void
}

// Контрольная без подсказок — выделенная карточка AiPlus (selected: бренд-бордер
// + bg-light-brand-warning): эйбров + условие через KaTeX + поле + «Проверить».
// Промах — warning-Informer (поддержка, не наказание), ввод сохраняется.
export function VerificationCard({
  problem,
  wrong,
  attempts,
  onCheck,
  onResume,
}: VerificationCardProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!value.trim()) return
    onCheck(value)
  }

  const handleChange = (next: string) => {
    setValue(next)
    if (wrong) onResume()
  }

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-stroke-brand bg-bg-light-brand-warning p-4">
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-caption2-medium uppercase tracking-[0.1em] text-text-brand">
          Контрольная · {problem.micro_skill}
        </span>
        <ApTag status="default">без подсказок</ApTag>
      </div>

      <p className="text-h3 text-text-primary">
        <MathText text={problem.statement} />
      </p>

      <form onSubmit={handleSubmit} className="flex items-stretch gap-2.5">
        <input
          inputMode="decimal"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Твой ответ"
          aria-label="Введите ответ контрольной"
          autoComplete="off"
          className="font-num min-w-0 flex-1 rounded-lg border border-stroke-primary-disabled bg-bg-primary px-4 text-body tabular-nums text-text-primary placeholder:text-text-secondary outline-none focus:border-[1.5px] focus:border-stroke-brand"
          style={{ fontSize: '16px' }}
        />
        <ApButton type="submit" variant="filled" size="m" disabled={!value.trim()}>
          Проверить
        </ApButton>
      </form>

      {wrong && <RetryBanner attempts={attempts} />}
    </article>
  )
}

// Мягкий ретрай: warning-Informer, маскот подбадривает. Без красного, без стыда.
function RetryBanner({ attempts }: { attempts: number }) {
  const text =
    attempts >= 2
      ? 'Почти! Пересчитай ещё раз — помни про смену базы после первого шага.'
      : 'Чуть мимо — это нормально. Глянь числа и попробуй снова, ты близко.'

  return (
    <div className="reveal">
      <ApInformer
        type="warning"
        leading={<Mascot mood="oops" size={40} className="shrink-0" />}
        title="Почти"
      >
        {text}
      </ApInformer>
    </div>
  )
}
