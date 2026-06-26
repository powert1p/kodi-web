import { Mascot } from '../../components/Mascot'
import { ApInformer } from '../../components/ApInformer'
import { LEVEL_META, type DrillLevel } from './levelConfig'

interface LevelIntroProps {
  level: DrillLevel
}

// Интро уровня: маскот «Кёди» + рамочная строка growth-mindset в его голосе.
// Оформлено как warning-Informer AiPlus (мягкая бренд-подложка) — уровень
// выводится из mastery (см. levelConfig).
export function LevelIntro({ level }: LevelIntroProps) {
  const meta = LEVEL_META[level]

  return (
    <ApInformer
      type="warning"
      leading={<Mascot mood={meta.mood} size={40} className="shrink-0" />}
      title={meta.eyebrow}
    >
      {meta.line}
    </ApInformer>
  )
}
