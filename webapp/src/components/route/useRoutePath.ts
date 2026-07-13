import { useCallback, useEffect, useState, type RefObject } from 'react'

// Измеренная геометрия «маршрута маркером»: реальные центры узлов → рукописная
// SVG-кривая (Q…-сегменты с детерминированным дрожанием пера). Разбита на
// пройденную часть (solid, рисуется stroke-dashoffset) и план впереди (пунктир).
export interface RoutePath {
  viewW: number
  viewH: number
  /** Вся траектория (старт→финиш) — карандашный след-подложка, виден статично с 0с. */
  trace: string
  /** Пройдено: от старта до текущего узла (плотный штрих route-line). */
  done: string
  /** Впереди: от текущего до финиша (плотный пунктир). */
  todo: string
  /** Длина done-пути — для draw-анимации (dashoffset) поверх подложки. */
  doneLen: number
}

// Детерминированное «дрожание маркера» по индексу сегмента (sin-hash): стабильно
// между рендерами (в отличие от Math.random), но выглядит от руки.
function wobble(i: number, amp: number): number {
  const s = Math.sin((i + 1) * 12.9898) * 43758.5453
  return (s - Math.floor(s) - 0.5) * 2 * amp
}

interface Pt {
  x: number
  y: number
}

// Строит рукописную кривую через точки: между соседними узлами — квадратика с
// серединой, смещённой по горизонтали на wobble (перо ведёт не по линейке).
function buildPath(pts: Pt[], from: number, to: number, amp: number): string {
  if (to <= from) return ''
  let d = `M ${pts[from]!.x.toFixed(1)} ${pts[from]!.y.toFixed(1)}`
  let prevY = pts[from]!.y
  for (let i = from + 1; i <= to; i++) {
    const p = pts[i]!
    const midY = (prevY + p.y) / 2
    d += ` Q ${(p.x + wobble(i, amp)).toFixed(1)} ${midY.toFixed(1)} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`
    prevY = p.y
  }
  return d
}

/**
 * Измеряет центры узлов-маркеров и строит геометрию маршрута.
 * @param containerRef — контейнер (система координат SVG).
 * @param getMarkers — актуальный массив DOM-узлов маркеров (по порядку сверху вниз).
 * @param currentIndex — индекс текущего узла (граница solid/пунктир).
 * @param redrawKey — смена значения форсирует перемер (напр. активная ступень drill).
 */
export function useRoutePath(
  containerRef: RefObject<HTMLElement | null>,
  getMarkers: () => (HTMLElement | null)[],
  currentIndex: number,
  redrawKey: string | number,
): RoutePath | null {
  const [path, setPath] = useState<RoutePath | null>(null)

  const measure = useCallback(() => {
    const container = containerRef.current
    if (!container) return
    const markers = getMarkers().filter((m): m is HTMLElement => m !== null)
    if (markers.length < 2) return

    const base = container.getBoundingClientRect()
    const pts: Pt[] = markers.map((m) => {
      const r = m.getBoundingClientRect()
      return { x: r.left - base.left + r.width / 2, y: r.top - base.top + r.height / 2 }
    })

    const viewW = Math.max(1, Math.ceil(base.width))
    const viewH = Math.max(1, Math.ceil(base.height))
    const amp = 4
    const last = pts.length - 1
    const cur = Math.min(Math.max(currentIndex, 0), last)

    // Старт-«хвостик» чуть выше первого узла — линия входит в маршрут сверху.
    const stub = Math.min(22, pts[0]!.y)
    const startStub = `M ${pts[0]!.x.toFixed(1)} ${(pts[0]!.y - stub).toFixed(1)} L ${pts[0]!.x.toFixed(1)} ${pts[0]!.y.toFixed(1)} `
    // Вся траектория одним path — карандашный след-подложка (виден статично, не зависит
    // от draw): гарантирует, что маршрут читается на скриншоте в ЛЮБОЙ момент (R3 §1).
    const trace = startStub + buildPath(pts, 0, last, amp)
    const done = startStub + buildPath(pts, 0, cur, amp)
    const todo = buildPath(pts, cur, last, amp)

    // Длина done через временный path в оффскрин-SVG (getTotalLength надёжен только на path в DOM).
    const svgNS = 'http://www.w3.org/2000/svg'
    const tmp = document.createElementNS(svgNS, 'path')
    tmp.setAttribute('d', done)
    let doneLen = 0
    try {
      doneLen = tmp.getTotalLength()
    } catch {
      doneLen = viewH
    }

    setPath({ viewW, viewH, trace, done, todo, doneLen })
  }, [containerRef, getMarkers, currentIndex, redrawKey])

  useEffect(() => {
    let raf = 0
    const run = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(measure)
    }
    run()

    // Перемер после подгрузки шрифтов (Unbounded меняет метрики чисел-героев).
    if (typeof document !== 'undefined' && document.fonts?.ready) {
      void document.fonts.ready.then(run)
    }

    const container = containerRef.current
    let ro: ResizeObserver | null = null
    if (container && typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(run)
      ro.observe(container)
    }
    window.addEventListener('resize', run)
    return () => {
      cancelAnimationFrame(raf)
      ro?.disconnect()
      window.removeEventListener('resize', run)
    }
  }, [measure, containerRef])

  return path
}
