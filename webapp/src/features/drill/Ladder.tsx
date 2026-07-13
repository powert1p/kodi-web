import type { Rung } from '../../lib/ladder'
import { RungActive } from './RungActive'
import { RungSolved, RungLocked } from './RungQuiet'
import { RouteSpine, type RouteStop } from '../../components/route/RouteSpine'

interface LadderProps {
  rungs: readonly Rung[]
  hint: boolean
  showReveal: boolean
  /** Ключ ступени, вставленной последней (для тона баннера climb-down). */
  insertedKey: string | null
  /** Режим «По тетради» — прокидывается только в активную RungActive. */
  photoMode?: boolean
  onSubmit: (value: string) => void
}

// SIGNATURE (§2/§3): лесенка ступеней КАК вертикальный участок маршрута — 4 ступени =
// 4 отметки высоты на рукописной кривой. Активная ступень «защёлкивается» верным
// ответом и линия дорисовывается вверх (redrawKey = ключ активной ступени). Активная
// ступень — самая тяжёлая масса; запертые — призраки; финиш — флажок «вершины».
export function Ladder({ rungs, hint, showReveal, insertedKey, photoMode, onSubmit }: LadderProps) {
  // Стабильный 1-based номер по ОРИГИНАЛЬНЫМ шагам (easier не нумеруем).
  let originalCounter = 0
  const numbered = rungs.map((r) => {
    if (r.kind === 'original') originalCounter += 1
    return { rung: r, num: originalCounter }
  })

  const activeIndex = numbered.findIndex((n) => n.rung.status === 'active')
  const activeKey = numbered[activeIndex]?.rung.key ?? 'done'

  const stops: RouteStop[] = numbered.map(({ rung, num }) => ({
    key: rung.key,
    state:
      rung.status === 'solved' ? 'done' : rung.status === 'active' ? 'current' : 'todo',
    // easier-ступень (разминка) — без номера (пустой узел); оригинал — номер.
    label: rung.kind === 'easier' ? undefined : String(num),
    content:
      rung.status === 'active' ? (
        <RungActive
          rung={rung}
          index={num}
          hint={hint}
          showReveal={showReveal}
          justInserted={rung.key === insertedKey}
          photoMode={photoMode}
          onSubmit={onSubmit}
        />
      ) : rung.status === 'solved' ? (
        <RungSolved rung={rung} index={num} />
      ) : (
        <RungLocked rung={rung} index={num} />
      ),
  }))

  // Флажок «вершина: ошибка побеждена» — линия доходит до финиша.
  stops.push({
    key: 'summit',
    state: 'flag',
    content: (
      <div className="flex min-h-8 items-center">
        <span className="font-display text-caption1-medium text-brand-ink">
          Вершина: ошибка побеждена
        </span>
      </div>
    ),
  })

  return (
    <RouteSpine
      stops={stops}
      currentIndex={activeIndex < 0 ? stops.length - 1 : activeIndex}
      redrawKey={activeKey}
      ariaLabel="Ступени решения"
    />
  )
}
