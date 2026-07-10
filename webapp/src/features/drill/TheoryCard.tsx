import { useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { MathText } from '../../components/MathText'
import { ChecklistIcon, DownIcon } from '../../icons'
import { track } from '../../lib/telemetry'

interface TheoryCardProps {
  /** Узел, для телеметрии открытия. */
  nodeId: string
  /** Текст карточки метода (nodes.theory_ru): Метод/Пример/Ловушка. */
  theory: string
}

// Раскрывашка «Как решать?»: метод узла (nodes.theory_ru) под условием задачи.
// Secondary-кнопка (НЕ оранжевый primary — единственный primary-CTA экрана остаётся
// у активной ступени лесенки, canon §2 п.7). Рендер: сплит по \n\n на абзацы,
// **…** → <strong>, текстовые куски через MathText ($…$ и юникод-математика).
export function TheoryCard({ nodeId, theory }: TheoryCardProps) {
  const [open, setOpen] = useState(false)
  // Телеметрия — только при ПЕРВОМ раскрытии (не на каждый тап).
  const trackedRef = useRef(false)

  function toggle() {
    setOpen((v) => {
      const next = !v
      if (next && !trackedRef.current) {
        trackedRef.current = true
        void track('theory_opened', { node_id: nodeId })
      }
      return next
    })
  }

  return (
    <div className="flex flex-col gap-3">
      <ApButton variant="secondary" size="m" full onClick={toggle} aria-expanded={open}>
        <ChecklistIcon size={18} />
        Как решать?
        <span className={['transition-transform', open ? 'rotate-180' : ''].join(' ')}>
          <DownIcon size={16} />
        </span>
      </ApButton>

      {open && (
        <ApCard
          as="section"
          padding="m"
          className="reveal flex flex-col gap-2"
          style={{ '--reveal-delay': '0ms' } as CSSProperties}
          aria-label="Как решать"
        >
          {renderTheory(theory)}
        </ApCard>
      )}
    </div>
  )
}

// Абзацы (\n\n) → <p>; внутри абзаца **…** → <strong>, остальное — через MathText.
function renderTheory(theory: string): ReactNode {
  return theory.split('\n\n').map((para, i) => (
    <p key={i} className="text-study text-text">
      {renderInline(para)}
    </p>
  ))
}

// Разбивает абзац на жирные метки (**…**) и обычные куски (MathText для $…$).
function renderInline(paragraph: string): ReactNode[] {
  return paragraph
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((chunk, i) => {
      const bold = chunk.match(/^\*\*([^*]+)\*\*$/)
      if (bold) {
        return (
          <strong key={i} className="font-semibold text-ink">
            {bold[1]}
          </strong>
        )
      }
      return <MathText key={i} text={chunk} />
    })
}
