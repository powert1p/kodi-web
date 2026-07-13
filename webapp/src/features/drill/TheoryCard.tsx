import { useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { ApTag, type TagStatus } from '../../components/ApTag'
import { MathText } from '../../components/MathText'
import { ChecklistIcon, DownIcon } from '../../icons'
import { track } from '../../lib/telemetry'

interface TheoryCardProps {
  /** Узел, для телеметрии открытия. */
  nodeId: string
  /** Текст карточки метода (nodes.theory_ru): Метод/Пример/Ловушка. */
  theory: string
}

// «Как решать?» — метод узла под условием, СВЁРНУТ по умолчанию (§3). Secondary-кнопка
// (НЕ primary — единственный primary-CTA держит активная ступень). Раскрытый блок тонирован
// тише активной ступени (surface, не brand-soft-lift). Блоки Метод/Пример/Ловушка — цветокод
// (brand/success/attn ink-пары, K-A графт) + формулы-чипы ≥18px.
export function TheoryCard({ nodeId, theory }: TheoryCardProps) {
  const [open, setOpen] = useState(false)
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
          className="reveal flex flex-col"
          style={{ '--reveal-delay': '0ms' } as CSSProperties}
          aria-label="Как решать"
        >
          {renderTheory(theory)}
        </ApCard>
      )}
    </div>
  )
}

// Метка блока → статус тега (цветокод K-A): Метод=brand · Пример=success · Ловушка=attn.
function blockStatus(label: string): TagStatus {
  const l = label.trim().toLowerCase()
  if (l.startsWith('метод')) return 'brand'
  if (l.startsWith('пример')) return 'success'
  if (l.startsWith('ловушка')) return 'attn'
  return 'neutral'
}

// Абзацы (\n\n) → блоки. Ведущий **Метод/Пример/Ловушка** → цветной тег + тело;
// иначе — просто учебный абзац. Тело — study (≥18px) + формулы-чипы.
function renderTheory(theory: string): ReactNode {
  return theory.split('\n\n').map((para, i) => {
    const m = para.match(/^\*\*([^*]+)\*\*\s*[—–-]?\s*([\s\S]*)$/)
    const cls =
      i === 0
        ? 'flex flex-col gap-2 py-3 first:pt-1'
        : 'flex flex-col gap-2 border-t border-dashed border-grid-strong py-3'
    if (m) {
      const label = m[1]!.trim()
      const body = m[2]!.trim()
      return (
        <div key={i} className={cls}>
          <ApTag
            status={blockStatus(label)}
            className="font-display self-start uppercase tracking-[0.06em]"
          >
            {label}
          </ApTag>
          <p className="formula-body text-study text-text">{renderInline(body)}</p>
        </div>
      )
    }
    return (
      <p key={i} className={['formula-body text-study text-text', cls].join(' ')}>
        {renderInline(para)}
      </p>
    )
  })
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
