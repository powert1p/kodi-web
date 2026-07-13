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

// SIGNATURE «Маршрут маркером по клетке»: живая оранжевая кривая, прочерченная как
// будто маркером по клетчатой странице, ведёт через список честными отметками.
// Кривая строится по РЕАЛЬНЫМ центрам узлов (useRoutePath), рисуется stroke-dashoffset
// при входе; пройденное — solid, впереди — пунктир. reduced-motion → мгновенно.
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
  const todoRef = useRef<SVGPathElement>(null)

  const curIdx = useMemo(() => {
    if (typeof currentIndex === 'number') return currentIndex
    const i = stops.findIndex((s) => s.state === 'current')
    return i < 0 ? 0 : i
  }, [currentIndex, stops])

  const drawKey = redrawKey ?? stops.map((s) => s.key + s.state).join('|')
  const path = useRoutePath(containerRef, () => markersRef.current, curIdx, drawKey)

  // Draw-анимация (императивно — надёжнее, чем React-стейт для dashoffset).
  useEffect(() => {
    const done = doneRef.current
    const todo = todoRef.current
    if (!done || !path) return
    const reduce =
      typeof matchMedia !== 'undefined' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduce) {
      done.style.transition = 'none'
      done.style.strokeDasharray = ''
      done.style.strokeDashoffset = '0'
      if (todo) {
        todo.style.transition = 'none'
        todo.style.opacity = '0.5'
      }
      return
    }

    done.style.transition = 'none'
    done.style.strokeDasharray = String(path.doneLen)
    done.style.strokeDashoffset = String(path.doneLen)
    void done.getBoundingClientRect() // reflow
    done.style.transition = 'stroke-dashoffset 1s var(--ease-out-soft) 0.35s'
    done.style.strokeDashoffset = '0'

    if (todo) {
      todo.style.transition = 'none'
      todo.style.opacity = '0'
      void todo.getBoundingClientRect()
      todo.style.transition = 'opacity 0.6s ease 1s'
      todo.style.opacity = '0.5'
    }
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
          <path
            ref={todoRef}
            d={path.todo}
            fill="none"
            stroke="var(--brand)"
            strokeWidth={3.5}
            strokeLinecap="round"
            strokeDasharray="1 11"
            style={{ opacity: 0 }}
          />
          <path
            ref={doneRef}
            d={path.done}
            fill="none"
            stroke="var(--brand)"
            strokeWidth={5}
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
