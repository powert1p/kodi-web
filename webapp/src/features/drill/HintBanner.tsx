import { Mascot } from '../../components/Mascot'
import { ApInformer } from '../../components/ApInformer'

interface HintBannerProps {
  /** Сократическая подсказка — наводящий вопрос, НИКОГДА не финальный ответ. */
  text: string
  /** «easier» — climb-down: вставлена ступень попроще (info-тон вместо warning). */
  variant?: 'hint' | 'easier'
}

// Подсказка Кёди (AiPlus Informer): ободряющий наводящий вопрос. warning-тон
// (бренд) для hint, info-тон (синий «разберём») для вставленной лёгкой ступени.
// Появляется через reveal. Никогда не показывает ответ.
export function HintBanner({ text, variant = 'hint' }: HintBannerProps) {
  const isEasier = variant === 'easier'

  return (
    <div className="reveal">
      <ApInformer
        type={isEasier ? 'info' : 'warning'}
        leading={<Mascot mood={isEasier ? 'cheer' : 'think'} size={40} className="shrink-0" />}
        title={isEasier ? 'Спустимся на ступень ниже' : 'Подсказка Кёди'}
      >
        {text}
      </ApInformer>
    </div>
  )
}
