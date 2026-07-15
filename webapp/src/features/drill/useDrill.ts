// React-обвязка state machine лесенки. Ответы проверяет backend; клиент только
// применяет серверный или vision-вердикт и восстанавливает подтверждённые шаги.

import { useMemo, useRef, useState, useCallback, useEffect } from 'react'
import { createLadder } from '../../lib/ladder'
import { postStepAnswer } from '../../lib/api'
import type { StepDTO, StepVerdictKind } from '../../lib/types'

interface DrillContext {
  problemId: number
  decompIdx: number | null
}

export interface DrillLadder {
  rungs: ReturnType<typeof createLadder>['rungs']
  activeRung: ReturnType<typeof createLadder>['activeRung']
  hint: boolean
  hintText: string | null
  finished: boolean
  showReveal: boolean
  insertedKey: null
  solvedOriginals: number
  totalOriginals: number
  attempts: number
  checking: boolean
  error: string | null
  submit: (value: string) => Promise<void>
  applyPhotoVerdict: (verdict: StepVerdictKind, hint?: string | null) => void
}

export function useDrill(
  steps: StepDTO[],
  context: DrillContext,
  solvedStepNs: readonly number[] = [],
): DrillLadder {
  const [, setTick] = useState(0)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hintText, setHintText] = useState<string | null>(null)
  const pendingRef = useRef(false)
  const wrongStreakRef = useRef(0)
  const solvedKey = solvedStepNs.join(',')

  const ladder = useMemo(
    () => createLadder(steps, solvedStepNs),
    // solvedKey — стабильное содержимое массива из query, а не его identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [steps, solvedKey],
  )
  const totalOriginals = steps.length

  useEffect(() => {
    wrongStreakRef.current = 0
    pendingRef.current = false
    setChecking(false)
    setError(null)
    setHintText(null)
  }, [ladder])

  const applyResult = useCallback((correct: boolean, submittedValue?: string, hint?: string | null) => {
    ladder.resolve(correct, submittedValue)
    if (correct) {
      wrongStreakRef.current = 0
      setHintText(null)
    } else {
      wrongStreakRef.current += 1
      setHintText(hint ?? null)
    }
    setTick((value) => value + 1)
  }, [ladder])

  const submit = useCallback(async (value: string) => {
    const active = ladder.activeRung
    if (!active || pendingRef.current || !value.trim()) return

    pendingRef.current = true
    setChecking(true)
    setError(null)
    try {
      const result = await postStepAnswer({
        problem_id: context.problemId,
        decomp_idx: context.decompIdx,
        step_n: active.stepN,
        answer: value,
      })
      if (result.step_n !== active.stepN) throw new Error('Backend вернул другой шаг')
      applyResult(result.correct, value, result.hint)
    } catch {
      setError('Не удалось проверить шаг. Ответ сохранён в поле — проверь связь и повтори.')
    } finally {
      pendingRef.current = false
      setChecking(false)
    }
  }, [applyResult, context.decompIdx, context.problemId, ladder])

  const applyPhotoVerdict = useCallback((verdict: StepVerdictKind, hint?: string | null) => {
    if (verdict === 'match') applyResult(true)
    if (verdict === 'mismatch') applyResult(false, undefined, hint)
    // unsure не считается ошибкой: ученик может переснять или ввести ответ.
  }, [applyResult])

  const active = ladder.activeRung
  const solvedOriginals = ladder.rungs.filter(
    (rung) => rung.kind === 'original' && rung.status === 'solved',
  ).length

  return {
    rungs: ladder.rungs,
    activeRung: active,
    hint: ladder.hint,
    hintText,
    finished: ladder.finished,
    showReveal: wrongStreakRef.current >= 2 && !!active,
    insertedKey: null,
    solvedOriginals,
    totalOriginals,
    attempts: ladder.attempts,
    checking,
    error,
    submit,
    applyPhotoVerdict,
  }
}
