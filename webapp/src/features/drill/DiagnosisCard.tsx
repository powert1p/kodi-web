import { useState } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { DownIcon } from '../../icons'
import type { Diagnosis } from '../../lib/types'

interface DiagnosisCardProps {
  diagnosis: Diagnosis
  /** Подпись шага по номеру (для «нашёл на шаге N»). */
  stepLabel: (n: number) => string | null
  /** «не так? поправить» — вернуть ученика к ручному вводу. */
  onCorrect: () => void
}

// Карточка разбора по фото (AiPlus ap-card): найденный шаг — info-Informer
// (синий «разберём», не красный), причина в голосе Кёди (наводит, не отвечает),
// сворачиваемая «что я увидел» — транскрипция как чек с возможностью поправить.
export function DiagnosisCard({ diagnosis, stepLabel, onCorrect }: DiagnosisCardProps) {
  const [open, setOpen] = useState(false)
  const label = diagnosis.failed_step !== null ? stepLabel(diagnosis.failed_step) : null

  return (
    <article className="ap-card reveal flex flex-col gap-3 p-4">
      {/* Найденный шаг — info-баннер (синий «разберём») */}
      {label && (
        <ApInformer
          type="info"
          leading={<span className="text-sm leading-none">🔍</span>}
        >
          <span className="text-caption1-medium text-text-info">
            Нашёл, где сбилось: {label}
          </span>
        </ApInformer>
      )}

      {/* Причина в голосе Кёди — наводит, не отвечает */}
      <div className="flex items-start gap-2.5">
        <Mascot mood="think" size={44} className="shrink-0" />
        <p className="pt-0.5 text-caption1 text-text-primary">{diagnosis.cause_text}</p>
      </div>

      {/* «что я увидел» — транскрипция как чек, сворачиваемая */}
      <div className="rounded-lg bg-bg-tertiary p-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="text-caption1-medium text-text-secondary">
            Что я увидел на фото
          </span>
          <span className={`text-text-secondary transition-transform ${open ? 'rotate-180' : ''}`}>
            <DownIcon size={16} />
          </span>
        </button>
        {open && (
          <div className="mt-2.5 flex flex-col gap-2.5">
            <p className="font-num rounded-lg border border-dashed border-stroke-primary-disabled bg-bg-primary px-3 py-2 text-caption1 leading-relaxed text-text-primary">
              {diagnosis.transcription}
            </p>
            <button
              type="button"
              onClick={onCorrect}
              className="self-start text-caption1-medium text-text-brand underline decoration-2 underline-offset-2 hover:opacity-80"
            >
              Не так? Поправить вручную
            </button>
          </div>
        )}
      </div>

      {/* Дальше — вернуться к лесенке с этой подсказкой */}
      <ApButton variant="filled" size="m" block onClick={onCorrect}>
        Понял — продолжу шаги
      </ApButton>
    </article>
  )
}
