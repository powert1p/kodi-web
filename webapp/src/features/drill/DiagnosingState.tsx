import { Mascot } from '../../components/Mascot'

// Состояние «диагностирую»: Кёди думает + скелетон-shimmer карточки разбора (AiPlus ap-card).
export function DiagnosingState() {
  return (
    <div
      className="ap-card reveal flex flex-col gap-3 p-4"
      aria-busy="true"
      aria-label="Кёди разбирает фото решения"
    >
      <div className="flex items-center gap-3">
        <Mascot mood="think" size={48} className="bob shrink-0" />
        <div className="flex flex-col">
          <span className="text-title text-text-primary">Читаю твоё решение…</span>
          <span className="text-caption2 text-text-secondary">
            Ищу, на каком шаге сбилось
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="shimmer h-4 w-3/4 rounded-sm bg-bg-secondary" />
        <div className="shimmer h-4 w-full rounded-sm bg-bg-secondary" />
        <div className="shimmer h-4 w-5/6 rounded-sm bg-bg-secondary" />
      </div>
    </div>
  )
}
