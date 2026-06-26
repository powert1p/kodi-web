import type { CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'
import { VerificationCard } from './VerificationCard'
import { ClosureCelebration } from './ClosureCelebration'
import { useClosure } from './useClosure'
import { MOCK_VERIFICATION } from './mock'

// Closure (/closure/:taskId) — награда + проверка. После пройденной лесенки
// ученик решает контрольную на ТОТ ЖЕ навык (новые числа) БЕЗ подсказок.
// Верно → празднование + штамп «ЗАКРЫТО» + XP + «Дальше →» на Hub.
// Состояния: solving / wrong (мягкий ретрай) / correct (celebrate).
// MOCK-контрольная + answersMatch — флоу демонстрируем без живого бэка.
export function ClosurePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const problem = MOCK_VERIFICATION
  const closure = useClosure(problem)

  const isDone = closure.status === 'correct'

  return (
    <div className="flex flex-col gap-4">
      {/* Назад к срезу — тихая ghost-кнопка */}
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <Button3D
          variant="secondary"
          size="md"
          onClick={() => navigate('/')}
          className="self-start"
        >
          <svg
            viewBox="0 0 16 16"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M13 8H4M7 4 3 8l4 4" />
          </svg>
          К срезу
        </Button3D>
      </div>

      {isDone ? (
        <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
          <ClosureCelebration xp={problem.xp} microSkill={problem.micro_skill} />
        </div>
      ) : (
        <>
          {/* Интро: почти финал — закрепим, что разобрали */}
          <section
            className="card-flat reveal flex items-start gap-3 rounded-(--radius-card) p-4"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <Mascot mood="cheer" size={64} className="-mt-1 shrink-0" />
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="text-[0.66rem] font-extrabold uppercase tracking-[0.16em] text-primary-ink">
                Закрепление · {problem.topic_label}
              </span>
              <h1 className="font-display text-[1.5rem] font-black leading-[1.05] tracking-tight text-ink">
                Последний шаг
              </h1>
              <p className="text-sm font-bold leading-snug text-ink">
                Реши похожую сам — без подсказок. Получится — ошибка закрыта.
              </p>
            </div>
          </section>

          <div
            className="reveal"
            style={{ '--reveal-delay': '120ms' } as CSSProperties}
          >
            <VerificationCard
              problem={problem}
              wrong={closure.status === 'wrong'}
              attempts={closure.attempts}
              onCheck={closure.check}
              onResume={closure.resume}
            />
          </div>
        </>
      )}

      {taskId && (
        <span className="font-num self-center text-[0.62rem] font-bold tabular-nums text-ink-mute/70">
          {taskId}
        </span>
      )}
    </div>
  )
}
