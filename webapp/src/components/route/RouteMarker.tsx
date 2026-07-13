import type { CSSProperties, ReactNode, Ref } from 'react'

// Состояние узла маршрута: пройден / текущий / впереди / свёрнутый хвост / финиш.
export type RouteStopState = 'done' | 'current' | 'todo' | 'rest' | 'flag'

interface RouteMarkerProps {
  state: RouteStopState
  /** Порядковый индекс — задержка pop-появления. */
  index: number
  /** Метка внутри узла (номер / «+8»). */
  children?: ReactNode
  ref?: Ref<HTMLElement>
}

const VARIANT: Record<Exclude<RouteStopState, 'flag'>, string> = {
  done: 'route-node bg-brand text-on-brand',
  current: 'route-node bg-brand text-on-brand',
  todo: 'route-node border-2 border-grid-strong bg-paper text-label',
  rest: 'route-node border-2 border-dashed border-grid-strong bg-paper text-brand-ink',
}

// Отметка высоты на маршруте. Флажок финиша — без круга (иконка brand-ink).
// Текущий узел пульсирует (route-pulse). Появляется pop-масштабом со stagger.
export function RouteMarker({ state, index, children, ref }: RouteMarkerProps) {
  const popStyle = { '--pop-delay': `${180 + index * 80}ms` } as CSSProperties

  if (state === 'flag') {
    return (
      <span
        ref={ref as Ref<HTMLSpanElement>}
        aria-hidden
        className="route-node pop text-brand-ink"
        style={popStyle}
      >
        <FlagIcon />
      </span>
    )
  }

  return (
    <span
      ref={ref as Ref<HTMLSpanElement>}
      aria-hidden
      className={['pop', VARIANT[state]].join(' ')}
      style={popStyle}
    >
      {state === 'current' && (
        <span
          className="route-pulse pointer-events-none absolute rounded-full border-2 border-brand"
          style={{ inset: -6 }}
        />
      )}
      {children}
    </span>
  )
}

function FlagIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={20}
      height={20}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 21V4" />
      <path d="M6 4h11l-2 4 2 4H6" fill="currentColor" stroke="none" />
    </svg>
  )
}
