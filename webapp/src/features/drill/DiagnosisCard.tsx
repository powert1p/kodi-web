import { useState } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { ApCard } from '../../components/ApCard'
import { DownIcon } from '../../icons'
import type { Diagnosis } from '../../lib/types'

interface DiagnosisCardProps {
  diagnosis: Diagnosis
  /** Подпись шага по номеру (для «нашёл на шаге N»). */
  stepLabel: (n: number) => string | null
  /** «не так? поправить» — вернуть ученика к ручному вводу. */
  onCorrect: () => void
}

// Карточка разбора по фото: найденный шаг — neutral-информер (спокойный факт,
// не решение), причина в голосе Кёди (наводит, не отвечает, учебный текст ≥18px),
// сворачиваемая «что я увидел» — транскрипция как чек с возможностью поправить.
export function DiagnosisCard({ diagnosis, stepLabel, onCorrect }: DiagnosisCardProps) {
  const [open, setOpen] = useState(false)
  const label = diagnosis.failed_step !== null ? stepLabel(diagnosis.failed_step) : null

  return (
    <ApCard as="article" padding="m" className="flex flex-col gap-3">
      {/* Найденный шаг — спокойный факт, не вердикт */}
      {label && (
        <ApInformer tone="neutral" leading={<span className="text-sm leading-none">🔍</span>}>
          <span className="text-caption1-medium text-text">Нашёл, где сбилось: {label}</span>
        </ApInformer>
      )}

      {/* Причина в голосе Кёди — наводит, не отвечает */}
      <div className="flex items-start gap-3">
        <Mascot mood="thinking" size="s" className="shrink-0" />
        <p className="pt-0.5 text-study text-ink">{diagnosis.cause_text}</p>
      </div>

      {/* «что я увидел» — транскрипция как чек, сворачиваемая */}
      <div className="rounded-control bg-paper p-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="text-caption1-medium text-muted">Что я увидел на фото</span>
          <span className={`text-muted transition-transform ${open ? 'rotate-180' : ''}`}>
            <DownIcon size={16} />
          </span>
        </button>
        {open && (
          <div className="mt-3 flex flex-col gap-3">
            <p className="font-num rounded-control border border-dashed border-stroke bg-surface px-3 py-2 text-caption1 leading-relaxed text-text">
              {diagnosis.transcription}
            </p>
            <button
              type="button"
              onClick={onCorrect}
              className="self-start text-caption1-medium text-brand underline decoration-2 underline-offset-2 hover:opacity-80"
            >
              Не так? Поправить вручную
            </button>
          </div>
        )}
      </div>

      {/* Дальше — вернуться к лесенке с этой подсказкой */}
      <ApButton variant="primary" size="m" full onClick={onCorrect}>
        Понял — продолжу шаги
      </ApButton>
    </ApCard>
  )
}
