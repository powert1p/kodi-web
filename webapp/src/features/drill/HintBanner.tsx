import { Mascot } from '../../components/Mascot'

interface HintBannerProps {
  /** Сократическая подсказка — наводящий вопрос, НИКОГДА не финальный ответ. */
  text: string
  /** «inserted» — climb-down: вставлена ступень попроще (другой тон). */
  variant?: 'hint' | 'easier'
}

// Подсказка Кёди: ободряющий наводящий вопрос. Тёплая янтарная подложка
// для hint, синяя «разберём» для вставленной лёгкой ступени. Появляется
// через reveal (transform/opacity). Никогда не показывает ответ.
export function HintBanner({ text, variant = 'hint' }: HintBannerProps) {
  const isEasier = variant === 'easier'
  const tintVar = isEasier ? 'var(--color-revisit)' : 'var(--color-almost)'
  const inkVar = isEasier ? 'var(--color-revisit-ink)' : 'var(--color-almost-ink)'

  return (
    <div
      role="status"
      className="reveal flex items-start gap-2.5 rounded-(--radius-card) p-3"
      style={{
        backgroundColor: `color-mix(in oklab, ${tintVar} 12%, white)`,
        border: `1.5px solid color-mix(in oklab, ${tintVar} 30%, white)`,
      }}
    >
      <Mascot mood={isEasier ? 'cheer' : 'think'} size={40} className="shrink-0" />
      <div className="flex min-w-0 flex-col gap-0.5 pt-0.5">
        <span
          className="text-[0.6rem] font-extrabold uppercase tracking-[0.14em]"
          style={{ color: inkVar }}
        >
          {isEasier ? 'Спустимся на ступень ниже' : 'Подсказка Кёди'}
        </span>
        <p className="text-sm font-bold leading-snug text-ink">{text}</p>
      </div>
    </div>
  )
}
