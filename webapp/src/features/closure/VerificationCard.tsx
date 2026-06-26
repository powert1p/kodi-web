import { useState } from 'react'
import type { FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { Button3D } from '../../components/Button3D'
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

// Контрольная без подсказок — тихая карточка в тоне drill-RungActive:
// эйбров «контрольная» + условие через KaTeX + числовое поле + «Проверить».
// Промах оформлен янтарным «почти» (поддержка, не наказание), ввод сохраняется.
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
    <article className="card-flat flex flex-col gap-3 rounded-(--radius-card) p-4 ring-2 ring-primary/15">
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-[0.6rem] font-extrabold uppercase tracking-[0.14em] text-primary-ink">
          Контрольная · {problem.micro_skill}
        </span>
        <span className="shrink-0 whitespace-nowrap rounded-(--radius-pill) bg-surface-soft px-2 py-0.5 text-[0.62rem] font-extrabold text-ink-mute">
          без подсказок
        </span>
      </div>

      <p className="font-display text-[1.2rem] font-black leading-[1.15] tracking-tight text-ink">
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
          className="font-num min-w-0 flex-1 rounded-(--radius-field) border-[1.5px] border-border bg-surface-soft px-4 text-base font-extrabold tabular-nums text-ink placeholder:font-bold placeholder:text-ink-mute focus:border-primary focus:bg-surface"
        />
        <Button3D type="submit" variant="primary" size="lg" disabled={!value.trim()}>
          Проверить
        </Button3D>
      </form>

      {wrong && <RetryBanner attempts={attempts} />}
    </article>
  )
}

// Мягкий ретрай: янтарный «почти», маскот подбадривает. Без красного, без стыда.
function RetryBanner({ attempts }: { attempts: number }) {
  const text =
    attempts >= 2
      ? 'Почти! Пересчитай ещё раз — помни про смену базы после первого шага.'
      : 'Чуть мимо — это нормально. Глянь числа и попробуй снова, ты близко.'

  return (
    <div
      role="status"
      className="reveal flex items-start gap-2.5 rounded-(--radius-card) p-3"
      style={{
        backgroundColor: 'color-mix(in oklab, var(--color-almost) 12%, white)',
        border: '1.5px solid color-mix(in oklab, var(--color-almost) 30%, white)',
      }}
    >
      <Mascot mood="oops" size={40} className="shrink-0" />
      <div className="flex min-w-0 flex-col gap-0.5 pt-0.5">
        <span className="text-[0.6rem] font-extrabold uppercase tracking-[0.14em] text-almost-ink">
          Почти
        </span>
        <p className="text-sm font-bold leading-snug text-ink">{text}</p>
      </div>
    </div>
  )
}
