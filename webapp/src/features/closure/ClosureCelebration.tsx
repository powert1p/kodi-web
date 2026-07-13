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

// Пик закрытия (§7 celebrate = флаг на вершине маршрута): рукописная кривая
// дорисована до флажка-вершины + маскот празднует + штамп «ЗАКРЫТО» + XP +
// primary-CTA «Дальше →» на Hub. Конфетти за карточкой.
export function ClosureCelebration({ xp }: ClosureCelebrationProps) {
  const navigate = useNavigate()

  return (
    <div className="relative">
      <Confetti />

      <ApCard as="article" padding="l" className="lift relative flex flex-col items-center gap-4 overflow-hidden text-center">
        {/* Штамп-печать «ЗАКРЫТО» — success-тон */}
        <span
          className="stamp absolute right-3 top-3 select-none rounded-chip border-2 border-success px-3 py-1 font-display text-caption2-medium uppercase tracking-[0.14em] text-success-ink"
          aria-hidden
        >
          Закрыто
        </span>

        {/* Флаг на вершине маршрута — линия дорисована до финиша */}
        <SummitFlag />

        <Mascot mood="celebrate" size="l" className="bob mascot-shadow" />

        <div className="flex flex-col gap-2">
          <h1 className="text-h2 text-ink">Ошибка закрыта!</h1>
          <p className="max-w-[17rem] text-study text-text">
            Ты разобрался сам, без подсказок — вершина взята.
          </p>
        </div>

        {/* Награда: один XP-акцент */}
        <div className="flex items-center gap-2 rounded-full bg-paper-2 px-4 py-2">
          <span className="text-attn-ink">
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

// Мини-маршрут к флажку-вершине: solid-кривая от подножия к флагу (сигнатура в финале).
function SummitFlag() {
  return (
    <svg viewBox="0 0 128 56" width={128} height={56} aria-hidden className="mt-1">
      <path
        d="M8 50 Q38 48 58 30 T112 14"
        fill="none"
        stroke="var(--brand)"
        strokeWidth={4}
        strokeLinecap="round"
      />
      <circle cx="8" cy="50" r="4" fill="var(--brand)" />
      <g stroke="var(--brand-ink)" strokeWidth={2.6} strokeLinecap="round">
        <path d="M112 14V2" fill="none" />
        <path d="M113 3h11l-3 4 3 4h-11z" fill="var(--brand)" stroke="none" />
      </g>
    </svg>
  )
}
