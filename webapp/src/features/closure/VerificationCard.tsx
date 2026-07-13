import { useState } from 'react'
import type { FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { ApTag } from '../../components/ApTag'
import { ApCard } from '../../components/ApCard'
import { Mascot } from '../../components/Mascot'

interface VerificationCardProps {
  /** Условие контрольной задачи (LaTeX инлайн в $...$). */
  statement: string
  /** Промах: показать мягкий ретрай-баннер (НИКОГДА красный). */
  wrong: boolean
  /** Сколько раз промахнулся — мягко меняет тон строки. */
  attempts: number
  /** Проверить ответ — правильность решает сервер (verification/answer). */
  onCheck: (value: string) => void
  /** Ввод изменился после промаха — вернуть в solving. */
  onResume: () => void
}

// Контрольная без подсказок — ApCard tone=brand-soft (единственный ДРУГОЙ активный
// фокус на этом экране, законно — это единственная интерактивная задача экрана):
// эйбров + условие через KaTeX + поле + «Проверить». Промах — attn-Informer
// (поддержка, не наказание, амбер — НИКОГДА красный), ввод сохраняется.
export function VerificationCard({
  statement,
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
    <ApCard as="article" tone="brand-soft" padding="m" className="lift flex flex-col gap-3 border-brand/40">
      <div className="flex items-center gap-2">
        <span className="font-display min-w-0 flex-1 truncate text-caption2-medium uppercase tracking-[0.1em] text-brand-ink">
          Контрольная
        </span>
        <ApTag status="neutral">без подсказок</ApTag>
      </div>

      <p className="formula-body text-study text-ink">
        <MathText text={statement} />
      </p>

      <form onSubmit={handleSubmit} className="flex items-stretch gap-3">
        <input
          inputMode="decimal"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Твой ответ"
          aria-label="Введите ответ контрольной"
          autoComplete="off"
          className="font-num min-w-0 flex-1 rounded-control border border-stroke bg-surface px-4 text-body tabular-nums text-text placeholder:text-muted outline-none focus:border-[1.5px] focus:border-brand"
          style={{ fontSize: '16px' }}
        />
        <ApButton type="submit" variant="primary" size="m" disabled={!value.trim()}>
          Проверить
        </ApButton>
      </form>

      {wrong && <RetryBanner attempts={attempts} />}
    </ApCard>
  )
}

// Мягкий ретрай: attn-Informer (амбер — «не сошлось», НИКОГДА красный),
// маскот подбадривает. Учебный текст (canon §1) — реплика Кёди ≥18px.
function RetryBanner({ attempts }: { attempts: number }) {
  const text =
    attempts >= 2
      ? 'Почти! Перечитай условие и проверь каждый шаг заново.'
      : 'Чуть мимо — это нормально. Глянь числа и попробуй снова, ты близко.'

  return (
    <div className="reveal">
      <ApInformer
        tone="attn"
        leading={<Mascot mood="oops" size="s" className="shrink-0" />}
        title="Почти"
      >
        <span className="text-study">{text}</span>
      </ApInformer>
    </div>
  )
}
