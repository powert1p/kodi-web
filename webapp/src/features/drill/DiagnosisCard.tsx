import { useState } from 'react'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'
import type { Diagnosis } from '../../lib/types'

interface DiagnosisCardProps {
  diagnosis: Diagnosis
  /** Подпись шага по номеру (для «нашёл на шаге N»). */
  stepLabel: (n: number) => string | null
  /** «не так? поправить» — вернуть ученика к ручному вводу. */
  onCorrect: () => void
}

// Карточка разбора по фото: найденный шаг подсвечен, поддерживающая причина
// в голосе Кёди (наводит, НЕ даёт финальный ответ), и сворачиваемая «что я
// увидел» — транскрипция как «чек» с возможностью поправить.
export function DiagnosisCard({ diagnosis, stepLabel, onCorrect }: DiagnosisCardProps) {
  const [open, setOpen] = useState(false)
  const label = diagnosis.failed_step !== null ? stepLabel(diagnosis.failed_step) : null

  return (
    <article className="card-flat reveal flex flex-col gap-3 rounded-(--radius-card) p-4">
      {/* Найденный шаг — подсвечен (синий «разберём», не красный) */}
      {label && (
        <div
          className="flex items-center gap-2 rounded-(--radius-field) px-3 py-2"
          style={{
            backgroundColor: 'color-mix(in oklab, var(--color-revisit) 12%, white)',
            border: '1.5px solid color-mix(in oklab, var(--color-revisit) 30%, white)',
          }}
        >
          <span aria-hidden className="text-sm leading-none">
            🔍
          </span>
          <span className="text-xs font-extrabold text-revisit-ink">
            Нашёл, где сбилось: {label}
          </span>
        </div>
      )}

      {/* Причина в голосе Кёди — наводит, не отвечает */}
      <div className="flex items-start gap-2.5">
        <Mascot mood="think" size={44} className="shrink-0" />
        <p className="pt-0.5 text-sm font-bold leading-snug text-ink">
          {diagnosis.cause_text}
        </p>
      </div>

      {/* «что я увидел» — транскрипция как чек, сворачиваемая */}
      <div className="rounded-(--radius-field) bg-surface-soft p-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="text-xs font-extrabold text-ink-mute">
            Что я увидел на фото
          </span>
          <svg
            viewBox="0 0 24 24"
            className={`size-4 text-ink-mute transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        {open && (
          <div className="mt-2.5 flex flex-col gap-2.5">
            <p className="font-num rounded-(--radius-field) border-[1.5px] border-dashed border-border bg-surface px-3 py-2 text-xs font-bold leading-relaxed text-ink">
              {diagnosis.transcription}
            </p>
            <button
              type="button"
              onClick={onCorrect}
              className="self-start text-xs font-extrabold text-primary-ink underline decoration-2 underline-offset-2 hover:text-primary"
            >
              Не так? Поправить вручную
            </button>
          </div>
        )}
      </div>

      {/* Дальше — вернуться к лесенке с этой подсказкой */}
      <Button3D variant="primary" size="lg" block onClick={onCorrect}>
        Понял — продолжу шаги
      </Button3D>
    </article>
  )
}
