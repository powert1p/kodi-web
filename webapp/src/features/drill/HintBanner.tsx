import { Mascot } from '../../components/Mascot'
import { ApInformer } from '../../components/ApInformer'

interface HintBannerProps {
  /** Сократическая подсказка — наводящий вопрос, НИКОГДА не финальный ответ. */
  text: string
  /** «easier» — climb-down: вставлена ступень попроще. */
  variant?: 'hint' | 'easier'
}

// Подсказка Кёди — спокойный neutral-информер (не бренд-подложка: акцент экрана
// держит только активная ступень, §1 дисциплина акцента). Появляется через reveal.
// Никогда не показывает ответ.
export function HintBanner({ text, variant = 'hint' }: HintBannerProps) {
  const isEasier = variant === 'easier'

  return (
    <div className="reveal">
      <ApInformer
        tone="neutral"
        leading={<Mascot mood={isEasier ? 'hi' : 'thinking'} size="s" className="shrink-0" />}
        title={isEasier ? 'Спустимся на ступень ниже' : 'Подсказка Кёди'}
      >
        {text}
      </ApInformer>
    </div>
  )
}
