import { Mascot } from '../../components/Mascot'

// Состояние «диагностирую»: Кёди думает + скелетон-shimmer карточки разбора.
// Появляется после сабмита фото; держит экран, пока vision «читает» решение.
export function DiagnosingState() {
  return (
    <div
      className="card-flat reveal flex flex-col gap-3 rounded-(--radius-card) p-4"
      aria-busy="true"
      aria-label="Кёди разбирает фото решения"
    >
      <div className="flex items-center gap-3">
        <Mascot mood="think" size={48} className="bob shrink-0" />
        <div className="flex flex-col">
          <span className="font-display text-base font-extrabold text-ink">
            Читаю твоё решение…
          </span>
          <span className="text-xs font-bold text-ink-mute">
            Ищу, на каком шаге сбилось
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="shimmer h-4 w-3/4 rounded-(--radius-pill) bg-surface-soft" />
        <div className="shimmer h-4 w-full rounded-(--radius-pill) bg-surface-soft" />
        <div className="shimmer h-4 w-5/6 rounded-(--radius-pill) bg-surface-soft" />
      </div>
    </div>
  )
}
