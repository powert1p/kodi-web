import { KodiBubble } from '../../components/KodiBubble'
import { LEVEL_META, type DrillLevel } from './levelConfig'

interface LevelIntroProps {
  level: DrillLevel
}

// Интро уровня — голос Кёди (§7 thinking): тёплый пузырь с меткой уровня и рамочной
// строкой growth-mindset. Уровень выводится из mastery (см. levelConfig).
export function LevelIntro({ level }: LevelIntroProps) {
  const meta = LEVEL_META[level]

  return (
    <KodiBubble mood={meta.mood} level={meta.eyebrow} size="s">
      {meta.line}
    </KodiBubble>
  )
}
