import { Mascot } from '../../components/Mascot'
import { RouteMeter } from '../../components/route/RouteMeter'

interface SrezHeaderProps {
  /** Позиция текущей задачи (1-based, приходит с сервера). */
  current: number
  total: number
}

// Шапка среза (§2/§7): присутствие Кёди в интро + ЧИСЛО-АЛЬТИМЕТР «N / 12» (Unbounded)
// + горизонтальный участок маршрута RouteMeter с честными 12 отметками. «Ты на N-й из 12».
export function SrezHeader({ current, total }: SrezHeaderProps) {
  return (
    <header className="flex flex-col gap-4 pt-1">
      <div className="flex items-center gap-3">
        <Mascot mood="hi" size="s" className="mascot-shadow shrink-0" />
        <div className="min-w-0">
          <p className="font-display text-caption1-medium uppercase tracking-[0.12em] text-brand-ink">
            Мини-срез
          </p>
          <p className="text-body text-text">
            Двенадцать коротких вопросов — по одному за раз, спокойно.
          </p>
        </div>
      </div>

      <div className="flex items-end gap-4">
        <span className="text-frac text-ink" aria-hidden>
          {current}
          <span className="den">/{total}</span>
        </span>
        <span className="flex-1 pb-2 text-caption1 text-muted">
          Отметка {current} из {total} на маршруте среза
        </span>
      </div>

      <RouteMeter current={current} total={total} ariaLabel={`Срез: вопрос ${current} из ${total}`} />
    </header>
  )
}
