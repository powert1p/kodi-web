import { Mascot } from '../../components/Mascot'
import { RouteMeter } from '../../components/route/RouteMeter'
import campStart from '../../assets/camp-start.jpg'

interface SrezHeaderProps {
  /** Позиция текущей задачи (1-based, приходит с сервера). */
  current: number
  total: number
}

// Шапка среза (§2/§7): тёплая полоса-иллюстрация мастерской (маркер + мандарины на
// клетке — снаряжение маршрута) со сплошным scrim держит первый вьюпорт (R3 §4 «дать
// якорь, сжать пустоту»); поверх — присутствие Кёди (18px, R3 §6) и ЧИСЛО-АЛЬТИМЕТР
// «N / 12». Ниже — горизонтальный участок маршрута RouteMeter с честными 12 отметками.
export function SrezHeader({ current, total }: SrezHeaderProps) {
  return (
    <header className="flex flex-col gap-4 pt-1">
      <section className="relative overflow-hidden rounded-card border border-stroke">
        {/* Иллюстрация-снаряжение + сплошной scrim под текстом (AA §10) */}
        <img
          src={campStart}
          alt=""
          aria-hidden
          className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        />
        <div className="hero-scrim pointer-events-none absolute inset-0" />

        <div className="relative flex items-start gap-3 p-4">
          <Mascot mood="hi" size="s" className="mascot-shadow shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="font-display text-caption1-medium uppercase tracking-[0.12em] text-brand-ink">
              Мини-срез
            </p>
            <p className="text-study text-text">
              Двенадцать коротких вопросов — по одному за раз, спокойно.
            </p>
          </div>
          <span className="text-frac shrink-0 self-end text-ink" aria-hidden>
            {current}
            <span className="den">/{total}</span>
          </span>
        </div>
      </section>

      <RouteMeter current={current} total={total} ariaLabel={`Срез: вопрос ${current} из ${total}`} />
    </header>
  )
}
