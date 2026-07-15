import type { CSSProperties } from 'react'

export type ProofNodeState = 'done' | 'active' | 'todo'

export interface ProofNode {
  key: string
  label: string
  state: ProofNodeState
}

interface ProofTraceProps {
  nodes: readonly ProofNode[]
  ariaLabel: string
  orientation?: 'horizontal' | 'vertical'
  tone?: 'cobalt' | 'bone'
  className?: string
  showLabels?: boolean
}

interface Point {
  x: number
  y: number
}

// Product signature V8: каждый узел приходит из реальных данных экрана.
// Компонент не добавляет декоративные точки и не вычисляет fake mastery.
export function ProofTrace({
  nodes,
  ariaLabel,
  orientation = 'horizontal',
  tone = 'cobalt',
  className = '',
  showLabels = false,
}: ProofTraceProps) {
  const safeNodes = nodes.length > 0 ? nodes : [{ key: 'empty', label: 'Нет точек', state: 'todo' as const }]
  const vertical = orientation === 'vertical'
  const viewBox = vertical ? '0 0 120 420' : '0 0 520 100'
  const points = makePoints(safeNodes.length, orientation)
  const path = makePath(points)
  const colorClass = tone === 'bone' ? 'text-surface' : 'text-ink'

  return (
    <figure
      className={['proof-trace', colorClass, className].filter(Boolean).join(' ')}
      role="img"
      aria-label={ariaLabel}
    >
      <svg viewBox={viewBox} preserveAspectRatio="none" aria-hidden>
        <path className="proof-trace__line-muted" d={path} pathLength={1} />
        <path className="proof-trace__line" d={path} pathLength={1} />

        {safeNodes.map((node, index) => {
          const point = points[index]!
          const active = node.state === 'active'
          const done = node.state === 'done'
          const delay = `${500 + index * 75}ms`

          return (
            <g
              key={node.key}
              className="proof-trace__node"
              style={{ '--proof-delay': delay } as CSSProperties}
            >
              {active && (
                <circle
                  className="proof-trace__active-ring"
                  cx={point.x}
                  cy={point.y}
                  r={vertical ? 20 : 14}
                  fill="none"
                  stroke="var(--brand)"
                  strokeWidth={3}
                  vectorEffect="non-scaling-stroke"
                />
              )}
              <circle
                cx={point.x}
                cy={point.y}
                r={vertical ? 11 : 8}
                fill={active ? 'var(--brand)' : done ? 'var(--success)' : 'var(--paper)'}
                stroke={done ? 'var(--success)' : 'currentColor'}
                strokeWidth={active ? 3 : 2}
                vectorEffect="non-scaling-stroke"
              />
              {active && (
                <path
                  d={`M ${point.x - 19} ${point.y - 19} L ${point.x - 12} ${point.y - 12} M ${point.x + 12} ${point.y + 12} L ${point.x + 19} ${point.y + 19}`}
                  stroke="var(--brand)"
                  strokeWidth={3}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
              {showLabels && (
                <text
                  x={point.x}
                  y={point.y + (vertical ? 3.5 : 3)}
                  textAnchor="middle"
                  fill={active ? 'var(--ink)' : done ? 'var(--surface)' : 'var(--cobalt-deep)'}
                  fontFamily="var(--font-display)"
                  fontSize={vertical ? 8 : 7}
                  fontWeight={800}
                >
                  {index + 1}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      <ol className="sr-only">
        {safeNodes.map((node) => (
          <li key={node.key}>{node.label}: {stateLabel(node.state)}</li>
        ))}
      </ol>
    </figure>
  )
}

function makePoints(count: number, orientation: 'horizontal' | 'vertical'): Point[] {
  if (orientation === 'vertical') {
    const top = 30
    const bottom = 390
    const span = count === 1 ? 0 : (bottom - top) / (count - 1)
    return Array.from({ length: count }, (_, index) => ({
      x: 60,
      y: count === 1 ? 92 : top + span * index,
    }))
  }

  const left = 32
  const right = 488
  const span = count === 1 ? 0 : (right - left) / (count - 1)
  return Array.from({ length: count }, (_, index) => ({
    x: count === 1 ? 130 : left + span * index,
    y: 50,
  }))
}

function makePath(points: readonly Point[]): string {
  if (points.length === 1) {
    const p = points[0]!
    return `M ${Math.max(0, p.x - 90)} ${p.y + 44} L ${p.x} ${p.y}`
  }
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

function stateLabel(state: ProofNodeState): string {
  if (state === 'done') return 'пройдено'
  if (state === 'active') return 'текущая точка'
  return 'впереди'
}
