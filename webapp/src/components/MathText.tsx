import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import katex from 'katex'

interface MathTextProps {
  /** Текст с инлайн-формулами в $...$. */
  text: string
  className?: string
}

interface Segment {
  type: 'text' | 'math'
  value: string
}

// Разбивает строку на текстовые и $...$-формульные сегменты.
function splitSegments(input: string): Segment[] {
  const out: Segment[] = []
  const re = /\$([^$]+)\$/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(input)) !== null) {
    if (m.index > last) {
      out.push({ type: 'text', value: input.slice(last, m.index) })
    }
    out.push({ type: 'math', value: m[1] ?? '' })
    last = re.lastIndex
  }
  if (last < input.length) {
    out.push({ type: 'text', value: input.slice(last) })
  }
  return out
}

// Рендер инлайн-математики. overflow-x живёт на ОБЁРТКЕ (.math-scroll),
// не на .katex — иначе появляется ложный вертикальный скролл.
export function MathText({ text, className }: MathTextProps) {
  const segments = useMemo(() => splitSegments(text), [text])

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return <span key={i}>{seg.value}</span>
        }
        return <FormulaSegment key={i} value={seg.value} />
      })}
    </span>
  )
}

function FormulaSegment({ value }: { value: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [overflowing, setOverflowing] = useState(false)
  const html = useMemo(() => katex.renderToString(value, {
    throwOnError: false,
    displayMode: false,
    output: 'html',
  }), [value])

  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const update = () => setOverflowing(element.scrollWidth > element.clientWidth + 1)
    update()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update)
    observer?.observe(element)
    if (document.fonts) void document.fonts.ready.then(update)
    return () => observer?.disconnect()
  }, [value])

  return (
    <>
      <wbr />
      <span className={['math-scroll-frame', overflowing ? 'math-scroll-frame--overflow' : ''].filter(Boolean).join(' ')}>
        <span
          ref={ref}
          className={['math-scroll inline-block max-w-full align-middle', overflowing ? 'math-scroll--long' : ''].filter(Boolean).join(' ')}
          tabIndex={overflowing ? 0 : undefined}
          role={overflowing ? 'region' : undefined}
          aria-label={overflowing ? 'Длинная формула. Прокрутите по горизонтали, чтобы увидеть полностью.' : undefined}
          // KaTeX-вывод доверенный (наш контент), рендерим как HTML.
          dangerouslySetInnerHTML={{ __html: html }}
        />
        {overflowing && <span className="math-scroll-cue" aria-hidden>↔</span>}
      </span>
    </>
  )
}
