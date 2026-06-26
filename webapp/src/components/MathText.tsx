import { useMemo } from 'react'
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
        const html = katex.renderToString(seg.value, {
          throwOnError: false,
          displayMode: false,
          output: 'html',
        })
        return (
          <span
            key={i}
            className="math-scroll inline-block max-w-full align-middle"
            // KaTeX-вывод доверенный (наш контент), рендерим как HTML.
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )
      })}
    </span>
  )
}
