import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import { track } from '../../lib/telemetry'
import { DrillHeader } from './DrillHeader'
import { LevelIntro } from './LevelIntro'
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
import { levelFromTask } from './levelConfig'
import { useWrongTask } from '../../lib/api'

// Drill (headline-экран): разбор ОДНОЙ ошибки по шагам лесенки.
// taskId берётся из /drill/:taskId, задача находится через useWrongTask(id)
// (переиспользует кэш Hub — не делает дополнительный запрос).
// Лесенка драйвится createLadder() через useDrill. Единственный вход сдачи —
// активная ступень: текстовый ввод («Ввод») или фото шага («По тетради»).
export function DrillPage() {
  // Читаем taskId из маршрута /drill/:taskId
  const { taskId } = useParams<{ taskId: string }>()

  // Выбираем задачу из кэша wrong-tasks по id
  const { data: task, isLoading, isError } = useWrongTask(taskId ?? '')

  // Состояние: загрузка
  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-muted">Загружаем задачу…</p>
      </div>
    )
  }

  // Состояние: ошибка запроса
  if (isError) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-muted">Не удалось загрузить задачи. Попробуй обновить страницу.</p>
      </div>
    )
  }

  // Состояние: задача не найдена по id (глубокая ссылка до загрузки кэша)
  if (!task) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-muted">Задача не найдена.</p>
      </div>
    )
  }

  // Задача загружена — рендерим Drill с реальными данными
  return <DrillContent task={task} />
}

// Вынесено отдельно чтобы хуки drill/flow вызывались только после того,
// как task гарантированно существует (правило хуков — нельзя условно вызывать).
import type { StepDTO, WrongTask } from '../../lib/types'
import { MOCK_EASIER_RUNG } from './mock'

function DrillContent({ task }: { task: WrongTask }) {
  const level = levelFromTask(task)

  // Есть ли у задачи боевая декомпозиция (шаги лесенки).
  const hasSteps = task.steps.length > 0

  // Задача без декомпозиции — не тупик: строим СИНТЕТИЧЕСКУЮ одноступенчатую
  // лесенку (один вход сдачи по ТЗ §1c). Ответ сверяется тем же createLadder,
  // фото-путь недоступен (decomp_idx null) — StepModeToggle/фото не монтируем.
  const steps = useMemo<StepDTO[]>(
    () =>
      hasSteps
        ? task.steps
        : [
            {
              n: 1,
              instruction_ru: 'Реши задачу в тетради и введи ответ',
              micro_skill: task.primary_micro_skill ?? '',
              micro_skill_label: task.primary_micro_skill_label,
              expected_value: task.answer,
              kind: 'compute',
              reveal: null,
            },
          ],
    [hasSteps, task.steps, task.primary_micro_skill, task.primary_micro_skill_label, task.answer],
  )

  const drill = useDrill(steps, MOCK_EASIER_RUNG)

  // Режим сдачи активной ступени: «Ввод» (дефолт) / «По тетради» (фото шага).
  // Фото-режим применим только к original-ступеням — на easier (климб-даун)
  // всегда остаётся текстовый ввод.
  const [mode, setMode] = useState<'input' | 'tetrad'>('input')
  const stepFlow = useStepSubmitFlow()
  const activeRung = drill.activeRung
  const isOriginalActive = activeRung?.kind === 'original'
  // choose-ступень (варианты ответа, напр. «новая/старая» цена) — фотографировать
  // нечего, фото-режим на неё не распространяется (решение директора). Тот же
  // маркер, что и в RungActive (isChoose): expected_value==='новая' на original-ступени.
  const isChooseActive = isOriginalActive && activeRung?.expected_value === 'новая'
  const photoMode = mode === 'tetrad' && isOriginalActive && !isChooseActive
  const activeStepN =
    activeRung && activeRung.kind === 'original' ? Number(activeRung.key.slice(1)) : null

  // Стухший stepFlow: при смене активной ступени (correct/climb-down/climb-back)
  // панель не должна монтироваться со старым mismatch/unsure-вердиктом предыдущего
  // шага — сбрасываем flow на каждую смену activeRung.
  useEffect(() => {
    stepFlow.reset()
    // eslint-disable-next-line -- намеренно: реагируем только на смену активной ступени
  }, [activeRung?.key])

  // Мост вердикта фото-шага в машину лесенки: match/mismatch реюзают
  // существующие пути ladder.submit (correct/wrong — climb-down и hint работают
  // как обычно), unsure машину НЕ трогает — это не ошибка, а «не разглядел»,
  // ждём повторного фото того же шага (телеметрия retry — в StepSubmitPanel,
  // на фактическом повторном фото, не здесь на приходе вердикта).
  useEffect(() => {
    if (stepFlow.status !== 'result' || !stepFlow.verdict || !activeRung) return
    const v = stepFlow.verdict
    void track('step_photo_verdict', {
      verdict: v.verdict,
      decomp_idx: task.decomp_idx,
      step_n: v.step_n,
    })
    if (v.verdict === 'match') {
      // Значение НЕ показываем юзеру — используется только для сравнения в ladder.submit.
      drill.submit(activeRung.expected_value)
      stepFlow.reset()
    } else if (v.verdict === 'mismatch') {
      // Сентинел не сопадёт ни с одним expected_value — гарантированный «wrong»,
      // реюз climb-down/hint; сам сентинел юзеру нигде не показывается.
      drill.submit('nomatch')
    }
    // eslint-disable-next-line -- намеренно узкие deps: реагируем только на смену вердикта фото-шага
  }, [stepFlow.status, stepFlow.verdict])

  // Прогресс шапки: решённые оригиналы +1 (текущий), но не больше всего.
  const current = Math.min(drill.solvedOriginals + 1, drill.totalOriginals)

  // Телеметрия открытия/ухода с drill. finishedRef держит актуальный статус
  // разбора для cleanup-эффекта: unmount без завершения → drill_left.
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

  return (
    <div className="flex flex-col gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <DrillHeader
          topic={task.topic_label}
          current={current}
          total={drill.totalOriginals}
        />
      </div>

      {!drill.finished && (
        <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
          <LevelIntro level={level} />
        </div>
      )}

      <div className="reveal" style={{ '--reveal-delay': '120ms' } as CSSProperties}>
        <ProblemCard statement={task.statement} wrongAnswer={task.wrong_answer} />
      </div>

      {/* «Как решать?» — метод узла под условием; null → кнопки нет (карточек 57/114). */}
      {task.theory_ru && (
        <div className="reveal" style={{ '--reveal-delay': '180ms' } as CSSProperties}>
          <TheoryCard nodeId={task.node_id} theory={task.theory_ru} />
        </div>
      )}

      {/* Лесенка: боевая декомпозиция или синтетическая одноступенчатая. */}
      {drill.finished ? (
        <FinishedCard taskId={task.id} answer={task.answer} />
      ) : (
        <div
          className="reveal flex flex-col gap-4"
          style={{ '--reveal-delay': '240ms' } as CSSProperties}
        >
          {/* Переключатель «Ввод»/«По тетради» и фото-путь — только для боевой
              декомпозиции: у синтетической ступени decomp_idx нет. */}
          {hasSteps && (
            <StepModeToggle
              mode={mode}
              onChange={(m) => {
                setMode(m)
                // Возврат в «Ввод» — сброс flow, чтобы стухший вердикт фото-шага
                // не всплыл, если пользователь снова переключится на «По тетради».
                if (m === 'input') stepFlow.reset()
                void track('step_mode_switched', { mode: m })
              }}
            />
          )}
          <Ladder
            rungs={drill.rungs}
            hint={drill.hint}
            showReveal={drill.showReveal}
            insertedKey={drill.insertedKey}
            photoMode={photoMode}
            onSubmit={drill.submit}
          />
          {hasSteps && photoMode && activeStepN !== null && (
            stepFlow.needsConsent ? (
              // 403 — сервер требует согласие родителя на фото шага (та же
              // карточка, что и в diagnose-ветке ниже).
              <ConsentCard onGranted={stepFlow.reset} onDismiss={stepFlow.reset} />
            ) : (
              <StepSubmitPanel
                stepN={activeStepN}
                status={stepFlow.status}
                verdict={stepFlow.verdict}
                onPhoto={(f) =>
                  void stepFlow.start(f, {
                    decomp_idx: task.decomp_idx!,
                    step_n: activeStepN,
                    problem_id: task.problem_id,
                  })
                }
                onRetry={stepFlow.reset}
              />
            )
          )}
          {/* Возврат чата Кёди: и для задач без ступеней тоже (при !finished). */}
          <AskKodiCard
            problemId={task.problem_id}
            decompIdx={task.decomp_idx}
            stepN={activeStepN}
          />
        </div>
      )}
    </div>
  )
}
