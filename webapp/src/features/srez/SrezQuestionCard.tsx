import { ApCard } from '../../components/ApCard'
import { ApTextField } from '../../components/ApTextField'
import { MathText } from '../../components/MathText'

interface SrezQuestionCardProps {
  topic: string
  /** Условие задачи (LaTeX инлайн в $...$) — учебный текст, MathText. */
  statement: string
  value: string
  disabled: boolean
  onChange: (value: string) => void
}

// Условие задачи среза: тема (muted caption) → учебный текст (≥18px) → поле
// ответа (ApTextField l=56, canon §1 — поле шага). Без CTA внутри карточки —
// «Проверить» общий для формы и живёт под карточкой (единственный primary экрана).
export function SrezQuestionCard({ topic, statement, value, disabled, onChange }: SrezQuestionCardProps) {
  return (
    <ApCard padding="m" className="flex flex-col gap-3">
      <span className="line-clamp-2 text-caption1 text-muted">Тема: {topic}</span>
      <p className="text-study text-ink">
        <MathText text={statement} />
      </p>
      <ApTextField
        fieldSize="l"
        inputMode="decimal"
        autoComplete="off"
        placeholder="Твой ответ"
        aria-label="Введите ответ"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </ApCard>
  )
}
