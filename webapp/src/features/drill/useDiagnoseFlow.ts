// Поток «фото → диагноз»: сжатие → useDiagnose() мутация → результат.
// Реальный путь useDiagnose сохранён; в DEV (бэк+vision не подключены) после
// короткой задержки подставляем MOCK_DIAGNOSIS, чтобы флоу был демонстрируем.
// 503 → состояние error (UI покажет поддерживающий fallback).

import { useState, useCallback } from 'react'
import { useDiagnose, ApiError } from '../../lib/api'
import { compressForUpload } from '../../lib/image'
import type { Diagnosis } from '../../lib/types'
import { MOCK_DIAGNOSIS } from './mock'

export type DiagnoseStatus = 'idle' | 'uploading' | 'diagnosing' | 'result' | 'error'

interface DiagnoseFlow {
  status: DiagnoseStatus
  diagnosis: Diagnosis | null
  /** true — ошибка была 503 (показываем worked-solution fallback). */
  is503: boolean
  start: (file: File, problemId: number) => Promise<void>
  reset: () => void
}

/** Имитация задержки vision в DEV-моке. */
const MOCK_DELAY_MS = 1400

export function useDiagnoseFlow(): DiagnoseFlow {
  const [status, setStatus] = useState<DiagnoseStatus>('idle')
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [is503, setIs503] = useState(false)
  const diagnose = useDiagnose()

  const start = useCallback(
    async (file: File, problemId: number) => {
      setIs503(false)
      setStatus('uploading')
      try {
        const photo = await compressForUpload(file)
        setStatus('diagnosing')

        try {
          // Реальный путь — сохранён. В DEV без бэка он упадёт сетевой ошибкой.
          const result = await diagnose.mutateAsync({ problem_id: problemId, photo })
          setDiagnosis(result)
          setStatus('result')
        } catch (err) {
          // 503 от живого бэка → поддерживающий fallback (worked-solution).
          if (err instanceof ApiError && err.status === 503) {
            setIs503(true)
            setStatus('error')
            return
          }
          // DEV без бэка/vision → демонстрируем мок-диагноз.
          if (import.meta.env.DEV) {
            await new Promise((r) => setTimeout(r, MOCK_DELAY_MS))
            setDiagnosis(MOCK_DIAGNOSIS)
            setStatus('result')
            return
          }
          throw err
        }
      } catch {
        setStatus('error')
      }
    },
    [diagnose],
  )

  const reset = useCallback(() => {
    setStatus('idle')
    setDiagnosis(null)
    setIs503(false)
  }, [])

  return { status, diagnosis, is503, start, reset }
}
