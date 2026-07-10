import { useState } from 'react'
import { ApButton } from '../../components/ApButton'
import { Mascot } from '../../components/Mascot'
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
    <div className="flex flex-col gap-3">
      <ApButton
        variant="secondary"
        size="m"
        full
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <Mascot mood="thinking" size="s" className="shrink-0" />
        Спросить Кёди
        <span className={['transition-transform', open ? 'rotate-180' : ''].join(' ')}>
          <DownIcon size={16} />
        </span>
      </ApButton>

      {open && <TutorPanel problemId={problemId} decompIdx={decompIdx} stepN={stepN} />}
    </div>
  )
}
