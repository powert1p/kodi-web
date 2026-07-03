import { Mascot } from '../../components/Mascot'
import { ApInformer } from '../../components/ApInformer'
import { LEVEL_META, type DrillLevel } from './levelConfig'

interface LevelIntroProps {
  level: DrillLevel
}

// Интро уровня: маскот «Кёди» + рамочная строка growth-mindset в его голосе.
// Спокойный neutral-тон (не decorative-бренд — brand зарезервирован под CTA, §1) —
// уровень выводится из mastery (см. levelConfig).
export function LevelIntro({ level }: LevelIntroProps) {
  const meta = LEVEL_META[level]

  return (
    <ApInformer
      tone="neutral"
      leading={<Mascot mood={meta.mood} size="s" className="shrink-0" />}
      title={meta.eyebrow}
    >
      {meta.line}
    </ApInformer>
  )
}
