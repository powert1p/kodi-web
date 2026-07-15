// Поток «фото шага → вердикт»: сжатие → useStepSubmit() мутация → результат.
// Аналог useDiagnoseFlow, но на уровне одного шага лесенки (Блок 1.2).
// 503 → состояние error (UI покажет поддерживающий fallback).

import { useState, useCallback, useRef } from 'react'
import { useStepSubmit, ApiError } from '../../lib/api'
import { compressForUpload } from '../../lib/image'
import { track } from '../../lib/telemetry'
import type { StepVerdict } from '../../lib/types'

export type StepSubmitStatus = 'idle' | 'uploading' | 'submitting' | 'result' | 'error'

/** Аргументы одного шага для проверки. */
export interface StepSubmitArgs {
  decomp_idx: number
  step_n: number
  problem_id: number
}

interface StepSubmitFlow {
  status: StepSubmitStatus
  verdict: StepVerdict | null
  /** true — ошибка была 503 (показываем поддерживающий fallback). */
  is503: boolean
  /** true — ошибка была 403: сервер требует согласие родителя (показываем ConsentCard, не generic-ошибку). */
  needsConsent: boolean
  submittedArgs: StepSubmitArgs | null
  start: (file: File, args: StepSubmitArgs) => Promise<void>
  reset: () => void
}

export function useStepSubmitFlow(): StepSubmitFlow {
  const [status, setStatus] = useState<StepSubmitStatus>('idle')
  const [verdict, setVerdict] = useState<StepVerdict | null>(null)
  const [is503, setIs503] = useState(false)
  const [needsConsent, setNeedsConsent] = useState(false)
  const [submittedArgs, setSubmittedArgs] = useState<StepSubmitArgs | null>(null)
  const requestIdRef = useRef(0)
  const pendingRef = useRef(false)
  const submit = useStepSubmit()

  const start = useCallback(
    async (file: File, args: StepSubmitArgs) => {
      if (pendingRef.current) return
      pendingRef.current = true
      const requestId = ++requestIdRef.current
      setIs503(false)
      setNeedsConsent(false)
      setVerdict(null)
      setSubmittedArgs(args)
      setStatus('uploading')
      void track('step_photo_submitted')
      try {
        const photo = await compressForUpload(file)
        if (requestId !== requestIdRef.current) return
        setStatus('submitting')

        try {
          const result = await submit.mutateAsync({ ...args, photo })
          if (requestId !== requestIdRef.current) return
          setVerdict(result)
          setStatus('result')
        } catch (err) {
          if (requestId !== requestIdRef.current) return
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
          throw err
        }
      } catch {
        if (requestId === requestIdRef.current) setStatus('error')
      } finally {
        if (requestId === requestIdRef.current) pendingRef.current = false
      }
    },
    [submit],
  )

  const reset = useCallback(() => {
    requestIdRef.current += 1
    pendingRef.current = false
    setStatus('idle')
    setVerdict(null)
    setIs503(false)
    setNeedsConsent(false)
    setSubmittedArgs(null)
  }, [])

  return { status, verdict, is503, needsConsent, submittedArgs, start, reset }
}
