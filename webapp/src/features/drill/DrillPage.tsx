import type { CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import { DrillHeader } from './DrillHeader'
import { LevelIntro } from './LevelIntro'
import { ProblemCard } from './ProblemCard'
import { Ladder } from './Ladder'
import { PhotoCapture } from './PhotoCapture'
import { DiagnosingState } from './DiagnosingState'
import { DiagnosisCard } from './DiagnosisCard'
import { DiagnosisError } from './DiagnosisError'
import { TutorPanel } from './TutorPanel'
import { FinishedCard } from './FinishedCard'
import { useDrill } from './useDrill'
import { useDiagnoseFlow } from './useDiagnoseFlow'
import { levelFromTask } from './levelConfig'
import { useWrongTask } from '../../lib/api'

// Drill (headline-экран): разбор ОДНОЙ ошибки по шагам + фото→диагноз.
// taskId берётся из /drill/:taskId, задача находится через useWrongTask(id)
// (переиспользует кэш Hub — не делает дополнительный запрос).
// Лесенка драйвится createLadder() через useDrill; фото-путь — через useDiagnoseFlow.
export function DrillPage() {
  // Читаем taskId из маршрута /drill/:taskId
  const { taskId } = useParams<{ taskId: string }>()

  // Выбираем задачу из кэша wrong-tasks по id
  const { data: task, isLoading, isError } = useWrongTask(taskId ?? '')

  // Состояние: загрузка
  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-text-secondary">Загружаем задачу…</p>
      </div>
    )
  }

  // Состояние: ошибка запроса
  if (isError) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-text-secondary">Не удалось загрузить задачи. Попробуй обновить страницу.</p>
      </div>
    )
  }

  // Состояние: задача не найдена по id (глубокая ссылка до загрузки кэша)
  if (!task) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-caption1 text-text-secondary">Задача не найдена.</p>
      </div>
    )
  }

  // Задача загружена — рендерим Drill с реальными данными
  return <DrillContent task={task} />
}

// Вынесено отдельно чтобы хуки drill/flow вызывались только после того,
// как task гарантированно существует (правило хуков — нельзя условно вызывать).
import type { WrongTask } from '../../lib/types'
import { MOCK_EASIER_RUNG } from './mock'

function DrillContent({ task }: { task: WrongTask }) {
  const level = levelFromTask(task)

  // Если шагов нет (задача не декомпозирована) — передаём пустой массив;
  // лесенка не рендерится, но фото→диагноз всё равно доступен.
  const drill = useDrill(task.steps, MOCK_EASIER_RUNG)
  const flow = useDiagnoseFlow()

  // Прогресс шапки: решённые оригиналы +1 (текущий), но не больше всего.
  const current = Math.min(drill.solvedOriginals + 1, drill.totalOriginals)

  // Подпись шага по номеру (для диагноза «нашёл на шаге N»).
  const stepLabel = (n: number): string | null => {
    const step = task.steps.find((s) => s.n === n)
    return step ? `шаг ${n} — ${step.micro_skill.toLowerCase()}` : `шаг ${n}`
  }

  // Опора для 503-fallback — reveal активного шага (не финальный ответ задачи).
  const fallbackHint = drill.activeRung?.reveal ?? null

  const showPhotoPath = !drill.finished

  // Есть ли ступени для лесенки
  const hasSteps = task.steps.length > 0

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

      {/* Лесенка: только если есть шаги */}
      {hasSteps && (
        drill.finished ? (
          <FinishedCard taskId={task.id} answer={task.answer} />
        ) : (
          <div
            className="reveal flex flex-col gap-4"
            style={{ '--reveal-delay': '180ms' } as CSSProperties}
          >
            <Ladder
              rungs={drill.rungs}
              hint={drill.hint}
              showReveal={drill.showReveal}
              insertedKey={drill.insertedKey}
              onSubmit={drill.submit}
            />
          </div>
        )
      )}

      {/* Фото-путь (headline) — пока лесенка не пройдена */}
      {showPhotoPath && (
        <section className="flex flex-col gap-3 pt-1">
          {flow.status === 'idle' && (
            <PhotoCapture
              onPhoto={(file) => void flow.start(file, task.problem_id)}
            />
          )}

          {(flow.status === 'uploading' || flow.status === 'diagnosing') && (
            <DiagnosingState />
          )}

          {flow.status === 'result' && flow.diagnosis && (
            <>
              <DiagnosisCard
                diagnosis={flow.diagnosis}
                stepLabel={stepLabel}
                onCorrect={flow.reset}
              />
              <TutorPanel problemId={task.problem_id} decompIdx={task.decomp_idx} />
            </>
          )}

          {flow.status === 'error' && (
            <DiagnosisError
              fallbackHint={fallbackHint}
              onRetry={flow.reset}
              onDismiss={flow.reset}
            />
          )}
        </section>
      )}
    </div>
  )
}
