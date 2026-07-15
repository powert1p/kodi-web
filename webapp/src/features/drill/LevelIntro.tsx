import { Mascot } from '../../components/Mascot'
import { LEVEL_META, type DrillLevel } from './levelConfig'

interface LevelIntroProps {
  level: DrillLevel
}

export function LevelIntro({ level }: LevelIntroProps) {
  const meta = LEVEL_META[level]

  return (
    <div className="flex items-center gap-3 border border-on-cobalt/25 bg-cobalt px-4 py-3">
      <Mascot mood={meta.mood} size="s" className="shrink-0" />
      <div>
        <p className="font-display text-caption2-medium uppercase tracking-[0.08em] text-brand">{meta.eyebrow}</p>
        <p className="mt-1 text-caption1 text-on-cobalt">{meta.line}</p>
      </div>
    </div>
  )
}
