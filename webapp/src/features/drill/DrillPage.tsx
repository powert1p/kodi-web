import type { CSSProperties } from 'react'
import { DrillHeader } from './DrillHeader'
import { LevelIntro } from './LevelIntro'
import { ProblemCard } from './ProblemCard'
import { Ladder } from './Ladder'
import { PhotoCapture } from './PhotoCapture'
import { DiagnosingState } from './DiagnosingState'
import { DiagnosisCard } from './DiagnosisCard'
import { DiagnosisError } from './DiagnosisError'
import { FinishedCard } from './FinishedCard'
import { useDrill } from './useDrill'
import { useDiagnoseFlow } from './useDiagnoseFlow'
import { levelFromTask } from './levelConfig'
import { MOCK_DRILL_TASK, MOCK_EASIER_RUNG } from './mock'

// Drill (headline-экран): разбор ОДНОЙ ошибки по шагам + фото→диагноз.
// MOCK-задача (проценты) + mock-диагноз делают флоу полностью демонстрируемым,
// пока живой бэк/vision не подключены. Лесенка драйвится createLadder()
// через useDrill; фото-путь — через useDiagnoseFlow.
export function DrillPage() {
  const task = MOCK_DRILL_TASK
  const level = levelFromTask(task)
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

      {drill.finished ? (
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
            <DiagnosisCard
              diagnosis={flow.diagnosis}
              stepLabel={stepLabel}
              onCorrect={flow.reset}
            />
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
