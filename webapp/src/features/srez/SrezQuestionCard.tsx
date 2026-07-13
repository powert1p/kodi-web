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

// Условие задачи среза (ведущая карточка, крафт-lift-sm): тема (display-эйбров) →
// учебный текст ≥18px + формулы-чипы → поле ответа (l=56, canon §1). Плейсхолдер
// формат-нейтральный «Твой ответ» (§4: без чисел/единиц/утечек); ответ на клиент не
// приходит (§2.5). CTA «Проверить» — под карточкой (единственный primary экрана).
export function SrezQuestionCard({ topic, statement, value, disabled, onChange }: SrezQuestionCardProps) {
  return (
    <ApCard padding="m" className="lift-sm flex flex-col gap-3">
      <span className="font-display text-caption2-medium uppercase tracking-[0.12em] text-brand-ink">
        Тема · {topic}
      </span>
      <p className="formula-body text-study text-ink">
        <MathText text={statement} />
      </p>
      {/* text (не decimal): в банке есть дроби «1/2» и отрицательные — iOS decimal
          не содержит «/» и «−»; text покрывает всё (§4: тип ответа → text). */}
      <ApTextField
        fieldSize="l"
        inputMode="text"
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
