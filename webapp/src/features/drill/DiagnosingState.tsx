import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'

// Состояние «диагностирую»: Кёди думает + скелетон-shimmer карточки разбора.
export function DiagnosingState() {
  return (
    <ApCard
      padding="m"
      className="reveal flex flex-col gap-3"
      aria-busy="true"
      aria-label="Кёди разбирает фото решения"
    >
      <div className="flex items-center gap-3">
        <Mascot mood="thinking" size="s" className="bob shrink-0" />
        <div className="flex flex-col">
          <span className="text-title text-ink">Читаю твоё решение…</span>
          <span className="text-caption2 text-muted">Ищу, на каком шаге сбилось</span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="shimmer h-4 w-3/4 rounded-chip bg-paper" />
        <div className="shimmer h-4 w-full rounded-chip bg-paper" />
        <div className="shimmer h-4 w-5/6 rounded-chip bg-paper" />
      </div>
    </ApCard>
  )
}
