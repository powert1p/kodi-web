import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { StepDTO, WrongTask } from '../../lib/types'
import { track } from '../../lib/telemetry'
import { useDrillState, useWrongTask } from '../../lib/api'
import { DrillHeader } from './DrillHeader'
import { FocusTopbar } from '../../components/FocusTopbar'
import { ProblemCard } from './ProblemCard'
import { TheoryCard } from './TheoryCard'
import { AskKodiCard } from './AskKodiCard'
import { Ladder } from './Ladder'
import { StepModeToggle } from './StepModeToggle'
import { StepSubmitPanel } from './StepSubmitPanel'
import { ConsentCard } from '../hub/ConsentCard'
import { FinishedCard } from './FinishedCard'
import { useDrill } from './useDrill'
import { useStepSubmitFlow } from './useStepSubmitFlow'
import { HubError } from '../hub/HubError'
import { ApButton } from '../../components/ApButton'

export function DrillPage() {
  const navigate = useNavigate()
  const { taskId } = useParams<{ taskId: string }>()
  const { data: task, isLoading, isError, refetch } = useWrongTask(taskId ?? '')

  if (isLoading) {
    return (
      <DrillFocusState>
        <div className="w-full" role="status" aria-label="Загружаем задачу">
          <div className="tape-card w-full px-6 py-8">
            <div className="shimmer h-3 w-32 bg-paper-2" />
            <div className="shimmer mt-5 h-10 w-full bg-paper-2" />
            <div className="shimmer mt-3 h-10 w-4/5 bg-paper-2" />
            <div className="shimmer mt-8 h-56 w-full rounded-card bg-surface" />
          </div>
        </div>
      </DrillFocusState>
    )
  }
  if (isError) {
    return <DrillFocusState><HubError onRetry={() => void refetch()} title="Разбор не загрузился" text="Проверь интернет и повтори. Место в ленте решения сохранилось." /></DrillFocusState>
  }
  if (!task) {
    return (
      <DrillFocusState>
        <section className="tape-card w-full px-6 py-8">
          <p className="text-mark text-brand-deep">Разбор недоступен</p>
          <h1 className="mt-4 text-h2 text-ink">Этой задачи уже нет в очереди.</h1>
          <p className="mt-4 text-study text-text">Вернись к учебному пути — там актуальный следующий шаг.</p>
          <ApButton className="mt-6" onClick={() => navigate('/')}>К моему пути</ApButton>
        </section>
      </DrillFocusState>
    )
  }
  return <DrillContent task={task} />
}

function DrillFocusState({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-paper">
      <FocusTopbar />
      <div className="mx-auto flex min-h-[calc(100dvh-4.5rem)] max-w-4xl items-center px-5 py-8">{children}</div>
    </div>
  )
}

function DrillContent({ task }: { task: WrongTask }) {
  const hasSteps = task.steps.length > 0
  const steps = useMemo<StepDTO[]>(
    () => hasSteps ? task.steps : [{
      n: 1,
      instruction_ru: 'Реши задачу в тетради и введи ответ',
      micro_skill: task.primary_micro_skill ?? '',
      micro_skill_label: task.primary_micro_skill_label,
      kind: 'compute',
      reveal: null,
    }],
    [hasSteps, task.steps, task.primary_micro_skill, task.primary_micro_skill_label],
  )
  const drillState = useDrillState(task.problem_id, task.decomp_idx)
  const drill = useDrill(
    steps,
    { problemId: task.problem_id, decompIdx: task.decomp_idx },
    drillState.data?.solved_step_ns ?? [],
  )
  const [mode, setMode] = useState<'input' | 'tetrad'>('input')
  const stepFlow = useStepSubmitFlow()
  const activeRung = drill.activeRung
  const isOriginalActive = activeRung?.kind === 'original'
  const isChooseActive = isOriginalActive && activeRung?.answerKind === 'choose'
  const photoMode = mode === 'tetrad' && isOriginalActive && !isChooseActive
  const activeStepN = activeRung?.kind === 'original' ? activeRung.stepN : null

  useEffect(() => {
    stepFlow.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- сброс только при смене активного шага
  }, [activeRung?.key])

  useEffect(() => {
    if (
      stepFlow.status !== 'result'
      || !stepFlow.verdict
      || !stepFlow.submittedArgs
      || !activeRung
      || activeRung.kind !== 'original'
      || stepFlow.submittedArgs.problem_id !== task.problem_id
      || stepFlow.submittedArgs.decomp_idx !== task.decomp_idx
      || stepFlow.submittedArgs.step_n !== activeRung.stepN
      || stepFlow.verdict.step_n !== activeRung.stepN
    ) return
    const verdict = stepFlow.verdict
    void track('step_photo_verdict', {
      verdict: verdict.verdict,
      decomp_idx: task.decomp_idx,
      step_n: verdict.step_n,
    })
    if (verdict.verdict === 'match') {
      drill.applyPhotoVerdict('match')
      stepFlow.reset()
    } else if (verdict.verdict === 'mismatch') {
      drill.applyPhotoVerdict('mismatch', verdict.hint)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- реагируем на новый verdict, не на объекты hook API
  }, [stepFlow.status, stepFlow.verdict])

  const current = Math.min(drill.solvedOriginals + 1, drill.totalOriginals)
  const openTrackedRef = useRef(false)
  const finishedRef = useRef(drill.finished)
  finishedRef.current = drill.finished

  useEffect(() => {
    if (!openTrackedRef.current) {
      openTrackedRef.current = true
      void track('drill_opened', { task_id: task.id })
    }
    return () => {
      if (!finishedRef.current) void track('drill_left', { task_id: task.id })
    }
  }, [task.id])

  if (drillState.isLoading) {
    return (
      <DrillFocusState>
        <div className="tape-card w-full px-6 py-8" role="status">Восстанавливаем ленту решения…</div>
      </DrillFocusState>
    )
  }
  if (drillState.isError) {
    return (
      <DrillFocusState>
        <HubError
          onRetry={() => void drillState.refetch()}
          title="Не удалось восстановить прогресс"
          text="Ни один шаг не потерян. Проверь интернет и повтори загрузку."
        />
      </DrillFocusState>
    )
  }

  return (
    <div className="min-h-dvh bg-paper">
      <DrillHeader topic={task.topic_label} current={current} total={drill.totalOriginals} />
      <div className="mx-auto max-w-6xl px-4 py-4 md:px-8 md:py-8">
        <ProblemCard
          topic={task.topic_label}
          statement={task.statement}
          wrongAnswer={task.wrong_answer}
        />

        {drill.finished ? (
          <div className="mt-6"><FinishedCard taskId={task.id} /></div>
        ) : (
          <section aria-label="Рабочая область" className="mt-5 grid min-w-0 gap-6 lg:mt-6 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
            <div className="min-w-0">
              {hasSteps && (
                <div className="mb-4 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-control border border-ink/15 bg-surface/70 px-3 py-2 sm:px-4 sm:py-3">
                  <div>
                    <p className="text-caption1-medium text-ink">Способ ответа</p>
                    <p className="hidden text-caption2 text-muted sm:block">Ввести ответ или показать только этот шаг в тетради.</p>
                  </div>
                  <StepModeToggle
                    mode={mode}
                    disabled={drill.checking || stepFlow.status === 'uploading' || stepFlow.status === 'submitting'}
                    onChange={(next) => {
                      setMode(next)
                      if (next === 'input') stepFlow.reset()
                      void track('step_mode_switched', { mode: next })
                    }}
                  />
                </div>
              )}

              <section aria-label="Пошаговый разбор">
                <Ladder
                  rungs={drill.rungs}
                  hint={drill.hint}
                  hintText={drill.hintText}
                  showReveal={drill.showReveal}
                  insertedKey={drill.insertedKey}
                  photoMode={photoMode}
                  hideLocked={photoMode}
                  checking={drill.checking}
                  onSubmit={(value) => drill.submit(value)}
                />
                {drill.error && (
                  <p className="mt-3 rounded-control border border-danger/30 bg-danger-soft px-4 py-3 text-caption1 text-danger-ink" role="alert">
                    {drill.error}
                  </p>
                )}
              </section>
            </div>

            <aside className="flex min-w-0 flex-col gap-4 rounded-card border border-ink/10 bg-sage-soft/55 p-4 lg:sticky lg:top-5">
              {hasSteps && photoMode && activeStepN !== null && (
                stepFlow.needsConsent ? (
                  <ConsentCard onGranted={stepFlow.reset} onDismiss={stepFlow.reset} />
                ) : (
                  <StepSubmitPanel
                    stepN={activeStepN}
                    status={stepFlow.status}
                    verdict={stepFlow.verdict}
                    onPhoto={(file) => void stepFlow.start(file, {
                      decomp_idx: task.decomp_idx!,
                      step_n: activeStepN,
                      problem_id: task.problem_id,
                    })}
                    onRetry={stepFlow.reset}
                  />
                )
              )}
              <AskKodiCard problemId={task.problem_id} decompIdx={task.decomp_idx} stepN={activeStepN} />
              {task.theory_ru && <TheoryCard nodeId={task.node_id} theory={task.theory_ru} />}
            </aside>
          </section>
        )}
      </div>
    </div>
  )
}
