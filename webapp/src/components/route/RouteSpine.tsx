import { useEffect, useMemo, useRef, type ReactNode } from 'react'
import { useRoutePath } from './useRoutePath'
import { RouteMarker } from './RouteMarker'
import type { RouteStopState } from './RouteMarker'

export interface RouteStop {
  key: string
  state: RouteStopState
  /** Метка внутри узла (номер ступени / «+8»); для flag игнорируется. */
  label?: ReactNode
  /** Тело справа от рельса. */
  content: ReactNode
}

interface RouteSpineProps {
  stops: RouteStop[]
  /** Индекс текущего узла (граница solid/пунктир). По умолчанию — первый 'current'. */
  currentIndex?: number
  /** Ширина колонки-рельса, px. */
  railWidth?: number
  ariaLabel?: string
  /** Смена → перерисовка (активная ступень drill). */
  redrawKey?: string | number
  className?: string
}

// SIGNATURE «Маршрут маркером по клетке»: живая линия, прочерченная как будто маркером
// по клетчатой странице, ведёт через список честными отметками. Кривая строится по
// РЕАЛЬНЫМ центрам узлов (useRoutePath). Три слоя (R3 §1): (1) карандашный след-подложка
// всей траектории — виден статично с 0с; (2) плотный пунктир плана; (3) прочерченный штрих
// пройденного — draw stroke-dashoffset ПОВЕРХ подложки как усиление, не как условие
// видимости. Маршрут читается на скриншоте в любой момент. reduced-motion → мгновенно.
export function RouteSpine({
  stops,
  currentIndex,
  railWidth = 44,
  ariaLabel,
  redrawKey,
  className = '',
}: RouteSpineProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const markersRef = useRef<(HTMLElement | null)[]>([])
  const doneRef = useRef<SVGPathElement>(null)

  const curIdx = useMemo(() => {
    if (typeof currentIndex === 'number') return currentIndex
    const i = stops.findIndex((s) => s.state === 'current')
    return i < 0 ? 0 : i
  }, [currentIndex, stops])

  const drawKey = redrawKey ?? stops.map((s) => s.key + s.state).join('|')
  const path = useRoutePath(containerRef, () => markersRef.current, curIdx, drawKey)

  // Draw-анимация пройденного (императивно — надёжнее React-стейта для dashoffset).
  // Подложка-след и пунктир видны СТАТИЧНО (в разметке ниже), draw лишь «дорисовывает»
  // штрих поверх. При reduced-motion штрих появляется мгновенно.
  useEffect(() => {
    const done = doneRef.current
    if (!done || !path) return
    const reduce =
      typeof matchMedia !== 'undefined' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduce) {
      done.style.transition = 'none'
      done.style.strokeDasharray = ''
      done.style.strokeDashoffset = '0'
      return
    }

    done.style.transition = 'none'
    done.style.strokeDasharray = String(path.doneLen)
    done.style.strokeDashoffset = String(path.doneLen)
    void done.getBoundingClientRect() // reflow
    done.style.transition = 'stroke-dashoffset 0.9s var(--ease-out-soft) 0.2s'
    done.style.strokeDashoffset = '0'
  }, [path])

  return (
    <div ref={containerRef} className={['relative', className].join(' ')}>
      {path && (
        <svg
          className="pointer-events-none absolute inset-0 overflow-visible"
          width={path.viewW}
          height={path.viewH}
          viewBox={`0 0 ${path.viewW} ${path.viewH}`}
          aria-hidden
        >
          {/* (1) карандашный след-подложка всей траектории — статично, виден с 0с */}
          <path
            d={path.trace}
            fill="none"
            stroke="var(--route-trace)"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* (2) плотный пунктир плана впереди — статично (opacity 0.7) */}
          <path
            d={path.todo}
            fill="none"
            stroke="var(--route-line)"
            strokeWidth={4}
            strokeLinecap="round"
            strokeDasharray="5 8"
            style={{ opacity: 0.7 }}
          />
          {/* (3) прочерченный штрих пройденного — draw поверх подложки */}
          <path
            ref={doneRef}
            d={path.done}
            fill="none"
            stroke="var(--route-line)"
            strokeWidth={5.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}

      <ol className="relative" aria-label={ariaLabel}>
        {stops.map((stop, i) => (
          <li
            key={stop.key}
            className="grid gap-3"
            style={{ gridTemplateColumns: `${railWidth}px minmax(0,1fr)` }}
          >
            <div className="flex justify-center">
              <RouteMarker
                ref={(el) => {
                  markersRef.current[i] = el
                }}
                state={stop.state}
                index={i}
              >
                {stop.label}
              </RouteMarker>
            </div>
            <div className="min-w-0 pb-4">{stop.content}</div>
          </li>
        ))}
      </ol>
    </div>
  )
}
