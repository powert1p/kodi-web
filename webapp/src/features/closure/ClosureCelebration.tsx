import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { StarFilledIcon, LongArrowRightIcon } from '../../icons'
import { Confetti } from './Confetti'

interface ClosureCelebrationProps {
  /** XP-награда за закрытие. */
  xp: number
}

// Пик закрытия: маскот празднует + штамп «ЗАКРЫТО» (success-тон) + начисленный
// XP + primary-CTA «Дальше →» на Hub. Конфетти за карточкой. Тема уже названа
// в шапке ClosurePage — micro_skill-код здесь больше не дублируем (canon §2 п.2).
export function ClosureCelebration({ xp }: ClosureCelebrationProps) {
  const navigate = useNavigate()

  return (
    <div className="relative">
      <Confetti />

      <ApCard as="article" padding="l" className="relative flex flex-col items-center gap-4 overflow-hidden text-center">
        {/* Штамп-печать «ЗАКРЫТО» — success-тон */}
        <span
          className="stamp absolute right-3 top-3 select-none rounded-chip border-2 border-success px-3 py-1 text-caption2-medium uppercase tracking-[0.14em] text-success"
          aria-hidden
        >
          Закрыто
        </span>

        <Mascot mood="celebrate" size="l" className="bob" />

        <div className="flex flex-col gap-2">
          <h1 className="text-h2 text-ink">Ошибка закрыта!</h1>
          <p className="max-w-[17rem] text-study text-text">
            Ты разобрался сам, без подсказок — мозг подкачался 💪
          </p>
        </div>

        {/* Награда: один XP-акцент (одна визуалка на карточку) */}
        <div className="flex items-center gap-2 rounded-full bg-paper px-4 py-2">
          <span className="text-attn">
            <StarFilledIcon size={18} />
          </span>
          <span className="font-num text-title tabular-nums text-ink">+{xp} XP</span>
        </div>

        <ApButton variant="primary" size="m" full onClick={() => navigate('/')}>
          Дальше
          <LongArrowRightIcon size={18} />
        </ApButton>
      </ApCard>
    </div>
  )
}
