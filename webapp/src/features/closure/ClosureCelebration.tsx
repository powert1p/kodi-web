import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'
import { Confetti } from './Confetti'

interface ClosureCelebrationProps {
  /** XP-награда за закрытие. */
  xp: number
  /** Ярлык навыка, который закрепили. */
  microSkill: string
}

// Пик закрытия: маскот празднует + механический штамп «ЗАКРЫТО» (signature) +
// начисленный XP + чанковая CTA «Дальше →» на Hub. Конфетти за карточкой.
// Вся «смелость» экрана — здесь; вокруг тихо.
export function ClosureCelebration({ xp, microSkill }: ClosureCelebrationProps) {
  const navigate = useNavigate()

  return (
    <div className="relative">
      <Confetti />

      <article className="card-flat relative flex flex-col items-center gap-4 overflow-hidden rounded-(--radius-card) px-5 py-7 text-center">
        {/* Штамп-печать «ЗАКРЫТО» — механический snap (signature-момент) */}
        <span
          className="stamp font-display absolute right-3 top-3 select-none rounded-(--radius-field) border-[2.5px] border-success px-2.5 py-1 text-[0.66rem] font-black uppercase tracking-[0.18em] text-got-ink"
          aria-hidden
        >
          Закрыто
        </span>

        <Mascot mood="celebrate" size={92} className="bob" />

        <div className="flex flex-col gap-1.5">
          <h1 className="font-display text-[1.7rem] font-black leading-[1.05] tracking-tight text-ink">
            Ошибка закрыта!
          </h1>
          <p className="max-w-[17rem] text-sm font-bold leading-snug text-ink-mute">
            Ты разобрался сам, без подсказок — мозг подкачался 💪
          </p>
        </div>

        {/* Награда: один крупный XP-числовой акцент (одна визуалка на карточку) */}
        <div className="flex items-center gap-2 rounded-(--radius-pill) bg-surface-soft px-4 py-2">
          <svg viewBox="0 0 24 24" className="size-5 text-secondary" aria-hidden>
            <path
              fill="currentColor"
              d="M12 2 9.3 8.6 2 9.2l5.5 4.8L5.8 21 12 17.1 18.2 21l-1.7-7 5.5-4.8-7.3-.6z"
            />
          </svg>
          <span className="font-num text-base font-extrabold tabular-nums text-ink">
            +{xp} XP
          </span>
          <span className="text-xs font-bold text-ink-mute">· {microSkill}</span>
        </div>

        <Button3D
          variant="success"
          size="lg"
          block
          onClick={() => navigate('/')}
        >
          Дальше
          <svg
            viewBox="0 0 16 16"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M3 8h9M9 4l4 4-4 4" />
          </svg>
        </Button3D>
      </article>
    </div>
  )
}
