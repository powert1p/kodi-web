import { useState } from 'react'
import { ApButton } from '../../components/ApButton'
import { DownIcon } from '../../icons'
import { TutorPanel } from './TutorPanel'

interface AskKodiCardProps {
  problemId: number
  decompIdx: number | null
  /** Активная ступень лесенки — прокидывается тьютору как фокус диалога. */
  stepN: number | null
}

// Раскрывашка «Спросить Кёди»: secondary-кнопка с маскотом (НЕ primary — акцент
// экрана держит активная ступень, canon §2 п.7) → внутри осиротевший TutorPanel.
// Телеметрию открытия панели ведёт сам TutorPanel (tutor_opened на монтирование).
export function AskKodiCard({ problemId, decompIdx, stepN }: AskKodiCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex flex-col gap-3 border-t border-stroke pt-5">
      <ApButton
        variant="secondary"
        size="m"
        full
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        Спросить AI-наставника
        <span className={['transition-transform', open ? 'rotate-180' : ''].join(' ')}>
          <DownIcon size={16} />
        </span>
      </ApButton>

      {open && <TutorPanel problemId={problemId} decompIdx={decompIdx} stepN={stepN} />}
    </div>
  )
}
