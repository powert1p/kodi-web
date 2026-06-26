import { Mascot } from '../../components/Mascot'
import { LEVEL_META, type DrillLevel } from './levelConfig'

interface LevelIntroProps {
  level: DrillLevel
}

// Интро уровня: маскот «Кёди» + рамочная строка growth-mindset в его голосе.
// Speech-облачко с тёплой подложкой; уровень выводится из mastery (см. levelConfig).
export function LevelIntro({ level }: LevelIntroProps) {
  const meta = LEVEL_META[level]

  return (
    <section className="flex items-start gap-3">
      <Mascot mood={meta.mood} size={64} className="-mt-1 shrink-0" />
      <div className="relative flex-1">
        {/* хвостик облачка */}
        <span
          aria-hidden
          className="absolute -left-1.5 top-4 size-3 rotate-45 rounded-[2px] border-b-[1.5px] border-l-[1.5px] border-border bg-surface-soft"
        />
        <div className="card-flat rounded-(--radius-card) bg-surface-soft p-3.5">
          <span className="text-[0.6rem] font-extrabold uppercase tracking-[0.14em] text-primary-ink">
            {meta.eyebrow}
          </span>
          <p className="mt-0.5 text-sm font-bold leading-snug text-ink">
            {meta.line}
          </p>
        </div>
      </div>
    </section>
  )
}
