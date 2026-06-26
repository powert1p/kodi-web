// Хук, связывающий чистую машину состояний createLadder() с React-рендером.
// createLadder мутирует внутренний state — здесь храним инстанс в ref и форсим
// перерисовку через tick. Дополнительно ведём счётчики для reveal и тон баннера.

import { useMemo, useRef, useState, useCallback } from 'react'
import { createLadder } from '../../lib/ladder'
import type { StepDTO } from '../../lib/types'
import type { EasierRung } from '../../lib/ladder'

export interface DrillLadder {
  rungs: ReturnType<typeof createLadder>['rungs']
  activeRung: ReturnType<typeof createLadder>['activeRung']
  hint: boolean
  finished: boolean
  /** Показать reveal активного шага (после ≥2 ошибок без climb-down). */
  showReveal: boolean
  /** Ключ только что вставленной easier-ступени (для тона баннера). */
  insertedKey: string | null
  /** Сколько ОРИГИНАЛЬНЫХ шагов решено (для прогресс-бара). */
  solvedOriginals: number
  /** Всего оригинальных шагов. */
  totalOriginals: number
  submit: (value: string) => void
}

export function useDrill(steps: StepDTO[], easier: EasierRung): DrillLadder {
  const ladderRef = useRef(createLadder(steps, easier))
  const [, setTick] = useState(0)
  const insertedRef = useRef<string | null>(null)
  // Счётчик подряд-ошибок на текущем активном шаге (для reveal).
  const wrongStreakRef = useRef(0)

  const ladder = ladderRef.current
  const totalOriginals = useMemo(() => steps.length, [steps])

  const submit = useCallback(
    (value: string) => {
      const beforeKeys = ladder.rungs.map((r) => r.key)
      const result = ladder.submit(value)

      if (result === 'correct') {
        wrongStreakRef.current = 0
        insertedRef.current = null
      } else if (result === 'inserted') {
        wrongStreakRef.current = 0
        // Найти ключ новой ступени (которой не было до сабмита).
        const afterKeys = ladder.rungs.map((r) => r.key)
        insertedRef.current = afterKeys.find((k) => !beforeKeys.includes(k)) ?? null
      } else {
        // wrong: копим стрик. Reveal — после 2-й ошибки, когда climb-down
        // невозможен (easier уже был или его нет).
        wrongStreakRef.current += 1
        insertedRef.current = null
      }

      setTick((t) => t + 1)
    },
    [ladder],
  )

  const active = ladder.activeRung
  // Reveal: на текущем активном шаге было ≥2 ошибки и climb-down не сработал.
  const showReveal = wrongStreakRef.current >= 2 && !!active

  const solvedOriginals = ladder.rungs.filter(
    (r) => r.kind === 'original' && r.status === 'solved',
  ).length

  return {
    rungs: ladder.rungs,
    activeRung: active,
    hint: ladder.hint,
    finished: ladder.finished,
    showReveal,
    insertedKey: insertedRef.current,
    solvedOriginals,
    totalOriginals,
    submit,
  }
}
