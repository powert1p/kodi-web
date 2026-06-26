import { useCallback, useState } from 'react'
import { answersMatch } from '../../lib/ladder'
import type { VerificationProblem } from './mock'

/** Статус закрепления: решает / ошибся (мягкий ретрай) / закрыл. */
export type ClosureStatus = 'solving' | 'wrong' | 'correct'

interface ClosureState {
  status: ClosureStatus
  /** Сколько раз промахнулся (для эмпатичного, не карающего тона). */
  attempts: number
  /** Проверить ответ — переводит статус в correct/wrong. */
  check: (value: string) => void
  /** Сбросить промах обратно в solving (после правки ввода). */
  resume: () => void
}

// Локальная машина закрепления: контрольная решается БЕЗ подсказок.
// Верный ответ → 'correct' (празднование + закрытие). Неверный → 'wrong'
// (мягкий ретрай, без стыда). Решение фиксируется в локальной session-памяти
// вызывающим кодом (onClosed) — здесь только статус.
export function useClosure(
  problem: VerificationProblem,
  onClosed?: () => void,
): ClosureState {
  const [status, setStatus] = useState<ClosureStatus>('solving')
  const [attempts, setAttempts] = useState(0)

  const check = useCallback(
    (value: string) => {
      if (answersMatch(value, problem.expected)) {
        setStatus('correct')
        onClosed?.()
        return
      }
      setAttempts((n) => n + 1)
      setStatus('wrong')
    },
    [problem.expected, onClosed],
  )

  const resume = useCallback(() => {
    setStatus((s) => (s === 'wrong' ? 'solving' : s))
  }, [])

  return { status, attempts, check, resume }
}
