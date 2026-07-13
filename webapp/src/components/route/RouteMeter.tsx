import { useEffect, useRef, useState } from 'react'

interface RouteMeterProps {
  /** Текущая отметка (1-based). */
  current: number
  /** Всего отметок маршрута (напр. 12 вопросов среза). */
  total: number
  ariaLabel?: string
}

// Горизонтальный участок маршрута для среза: рукописная линия по клетке с честными
// отметками (N точек = N вопросов) и флажком-финишем. Пройдено — solid, впереди —
// пунктир; линия дорисовывается stroke-dashoffset при входе. reduced-motion → мгновенно.
// Даёт «ты на 1-й из 12» тем же языком, что вертикальный RouteSpine на hub/drill.
export function RouteMeter({ current, total, ariaLabel }: RouteMeterProps) {
  const boxRef = useRef<HTMLDivElement>(null)
  const doneRef = useRef<SVGPathElement>(null)
  const todoRef = useRef<SVGPathElement>(null)
  const [w, setW] = useState(0)

  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    const update = () => setW(el.clientWidth)
    update()
    let ro: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(update)
      ro.observe(el)
    }
    return () => ro?.disconnect()
  }, [])

  const H = 40
  const padX = 16
  const cy = H / 2
  const slots = total // точки 0..total-1, слот total → флажок
  const usable = Math.max(1, w - padX * 2)
  const step = usable / slots
  const cur = Math.min(Math.max(current - 1, 0), total - 1)

  // Точки отметок + флажок.
  const pts = Array.from({ length: total }, (_, i) => ({
    x: padX + i * step,
    y: cy + wobble(i, 2.5),
  }))
  const flagX = padX + total * step

  const donePath = pathThrough(pts, 0, cur)
  const todoPath = pathThrough([...pts, { x: flagX, y: cy }], cur, total)

  // Draw при входе (императивно, как RouteSpine).
  useEffect(() => {
    const done = doneRef.current
    const todo = todoRef.current
    if (!done || w === 0) return
    const reduce =
      typeof matchMedia !== 'undefined' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      done.style.strokeDasharray = ''
      done.style.strokeDashoffset = '0'
      if (todo) todo.style.opacity = '0.5'
      return
    }
    let len = 0
    try {
      len = done.getTotalLength()
    } catch {
      len = usable
    }
    done.style.transition = 'none'
    done.style.strokeDasharray = String(len)
    done.style.strokeDashoffset = String(len)
    void done.getBoundingClientRect()
    done.style.transition = 'stroke-dashoffset 0.9s var(--ease-out-soft) 0.25s'
    done.style.strokeDashoffset = '0'
    if (todo) {
      todo.style.opacity = '0'
      void todo.getBoundingClientRect()
      todo.style.transition = 'opacity 0.6s ease 0.8s'
      todo.style.opacity = '0.5'
    }
  }, [w, cur, usable])

  return (
    <div
      ref={boxRef}
      className="ap-card lift-sm px-3 py-3"
      role="img"
      aria-label={ariaLabel ?? `Маршрут: отметка ${current} из ${total}`}
    >
      <svg width="100%" height={H} viewBox={`0 0 ${Math.max(w, 1)} ${H}`} aria-hidden>
        <path
          ref={todoRef}
          d={todoPath}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray="1 9"
          style={{ opacity: 0 }}
        />
        <path
          ref={doneRef}
          d={donePath}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={4.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {pts.map((p, i) => (
          <Node key={i} x={p.x} y={p.y} kind={i < cur ? 'done' : i === cur ? 'current' : 'todo'} />
        ))}
        {/* Флажок-финиш */}
        <g transform={`translate(${flagX - 4} ${cy - 11})`} stroke="var(--brand-ink)" strokeWidth={2.4} strokeLinecap="round">
          <path d="M0 22V0" fill="none" />
          <path d="M1 1h13l-3 4 3 4H1z" fill="var(--brand)" stroke="none" />
        </g>
      </svg>
    </div>
  )
}

function Node({ x, y, kind }: { x: number; y: number; kind: 'done' | 'current' | 'todo' }) {
  if (kind === 'current') {
    return (
      <g>
        <circle cx={x} cy={y} r={9} fill="none" stroke="var(--brand)" strokeWidth={2.2} opacity={0.5} className="route-pulse" style={{ transformOrigin: `${x}px ${y}px` }} />
        <circle cx={x} cy={y} r={5.4} fill="var(--brand)" stroke="var(--surface)" strokeWidth={2} />
      </g>
    )
  }
  if (kind === 'done') {
    return <circle cx={x} cy={y} r={5.4} fill="var(--brand)" />
  }
  return <circle cx={x} cy={y} r={5.5} fill="var(--paper)" stroke="var(--grid-strong)" strokeWidth={2.2} />
}

// Рукописная кривая через точки (Q-сегменты с горизонтальным дрожанием пера).
function pathThrough(pts: { x: number; y: number }[], from: number, to: number): string {
  if (to <= from || !pts[from]) return ''
  let d = `M ${pts[from]!.x.toFixed(1)} ${pts[from]!.y.toFixed(1)}`
  for (let i = from + 1; i <= to && pts[i]; i++) {
    const a = pts[i - 1]!
    const b = pts[i]!
    const mx = (a.x + b.x) / 2
    d += ` Q ${mx.toFixed(1)} ${(a.y + wobble(i, 2)).toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`
  }
  return d
}

function wobble(i: number, amp: number): number {
  const s = Math.sin((i + 1) * 12.9898) * 43758.5453
  return (s - Math.floor(s) - 0.5) * 2 * amp
}
