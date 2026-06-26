import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { StarFilledIcon, LongArrowRightIcon } from '../../icons'
import { Confetti } from './Confetti'

interface ClosureCelebrationProps {
  /** XP-награда за закрытие. */
  xp: number
  /** Ярлык навыка, который закрепили. */
  microSkill: string
}

// Пик закрытия: маскот празднует + штамп «ЗАКРЫТО» (мягкий AiPlus snap, success-тон) +
// начисленный XP + ApButton «Дальше →» на Hub. Конфетти за карточкой.
export function ClosureCelebration({ xp, microSkill }: ClosureCelebrationProps) {
  const navigate = useNavigate()

  return (
    <div className="relative">
      <Confetti />

      <article className="ap-card relative flex flex-col items-center gap-4 overflow-hidden px-5 py-7 text-center">
        {/* Штамп-печать «ЗАКРЫТО» — success-тон AiPlus */}
        <span
          className="stamp absolute right-3 top-3 select-none rounded-sm border-2 border-stroke-success px-2.5 py-1 text-caption2-medium uppercase tracking-[0.14em] text-text-success"
          aria-hidden
        >
          Закрыто
        </span>

        <Mascot mood="celebrate" size={92} className="bob" />

        <div className="flex flex-col gap-1.5">
          <h1 className="text-h2 text-text-primary">Ошибка закрыта!</h1>
          <p className="max-w-[17rem] text-caption1 text-text-secondary">
            Ты разобрался сам, без подсказок — мозг подкачался 💪
          </p>
        </div>

        {/* Награда: один XP-акцент (одна визуалка на карточку) */}
        <div className="flex items-center gap-2 rounded-full bg-bg-tertiary px-4 py-2">
          <span className="text-text-yellow">
            <StarFilledIcon size={18} />
          </span>
          <span className="font-num text-title tabular-nums text-text-primary">
            +{xp} XP
          </span>
          <span className="text-caption2 text-text-secondary">· {microSkill}</span>
        </div>

        <ApButton variant="filled" size="m" block onClick={() => navigate('/')}>
          Дальше
          <LongArrowRightIcon size={18} />
        </ApButton>
      </article>
    </div>
  )
}
