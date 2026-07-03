// Поток «фото шага → вердикт»: сжатие → useStepSubmit() мутация → результат.
// Аналог useDiagnoseFlow, но на уровне одного шага лесенки (Блок 1.2).
// Реальный путь useStepSubmit сохранён; в DEV (бэк+vision не подключены) после
// короткой задержки подставляем MOCK_STEP_VERDICT, чтобы флоу был демонстрируем.
// 503 → состояние error (UI покажет поддерживающий fallback).

import { useState, useCallback } from 'react'
import { useStepSubmit, ApiError } from '../../lib/api'
import { compressForUpload } from '../../lib/image'
import { track } from '../../lib/telemetry'
import type { StepVerdict } from '../../lib/types'
import { MOCK_STEP_VERDICT } from './mock'

export type StepSubmitStatus = 'idle' | 'uploading' | 'submitting' | 'result' | 'error'

/** Аргументы одного шага для проверки. */
interface StepSubmitArgs {
  decomp_idx: number
  step_n: number
  problem_id?: number
}

interface StepSubmitFlow {
  status: StepSubmitStatus
  verdict: StepVerdict | null
  /** true — ошибка была 503 (показываем поддерживающий fallback). */
  is503: boolean
  /** true — ошибка была 403: сервер требует согласие родителя (показываем ConsentCard, не generic-ошибку). */
  needsConsent: boolean
  start: (file: File, args: StepSubmitArgs) => Promise<void>
  reset: () => void
}

/** Имитация задержки vision в DEV-моке. */
const MOCK_DELAY_MS = 1400

export function useStepSubmitFlow(): StepSubmitFlow {
  const [status, setStatus] = useState<StepSubmitStatus>('idle')
  const [verdict, setVerdict] = useState<StepVerdict | null>(null)
  const [is503, setIs503] = useState(false)
  const [needsConsent, setNeedsConsent] = useState(false)
  const submit = useStepSubmit()

  const start = useCallback(
    async (file: File, args: StepSubmitArgs) => {
      setIs503(false)
      setNeedsConsent(false)
      setStatus('uploading')
      void track('step_photo_submitted')
      try {
        const photo = await compressForUpload(file)
        setStatus('submitting')

        try {
          // Реальный путь — сохранён. В DEV без бэка он упадёт сетевой ошибкой.
          const result = await submit.mutateAsync({ ...args, photo })
          setVerdict(result)
          setStatus('result')
        } catch (err) {
          // 403 — родитель ещё не дал согласие на фото → ConsentCard вместо generic-ошибки.
          if (err instanceof ApiError && err.status === 403) {
            setNeedsConsent(true)
            setStatus('error')
            return
          }
          // 503 от живого бэка → поддерживающий fallback.
          if (err instanceof ApiError && err.status === 503) {
            setIs503(true)
            setStatus('error')
            return
          }
          // DEV без бэка/vision → демонстрируем мок-вердикт.
          if (import.meta.env.DEV) {
            await new Promise((r) => setTimeout(r, MOCK_DELAY_MS))
            setVerdict(MOCK_STEP_VERDICT)
            setStatus('result')
            return
          }
          throw err
        }
      } catch {
        setStatus('error')
      }
    },
    [submit],
  )

  const reset = useCallback(() => {
    setStatus('idle')
    setVerdict(null)
    setIs503(false)
    setNeedsConsent(false)
  }, [])

  return { status, verdict, is503, needsConsent, start, reset }
}
