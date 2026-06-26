import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { LeftIcon } from '../../icons'
import { VerificationCard } from './VerificationCard'
import { ClosureCelebration } from './ClosureCelebration'
import { useClosure } from './useClosure'
import { MOCK_VERIFICATION } from './mock'

// Closure (/closure/:taskId) — награда + проверка. После пройденной лесенки
// ученик решает контрольную на ТОТ ЖЕ навык (новые числа) БЕЗ подсказок.
// Верно → празднование + штамп «ЗАКРЫТО» + XP + «Дальше →» на Hub.
// Состояния: solving / wrong (мягкий ретрай) / correct (celebrate).
export function ClosurePage() {
  const navigate = useNavigate()
  const problem = MOCK_VERIFICATION
  const closure = useClosure(problem)

  const isDone = closure.status === 'correct'

  return (
    <div className="flex flex-col gap-4">
      {/* Назад к срезу — outlined-кнопка AiPlus */}
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <ApButton
          variant="outlined"
          size="s"
          onClick={() => navigate('/')}
          className="self-start"
        >
          <LeftIcon size={16} />
          К срезу
        </ApButton>
      </div>

      {isDone ? (
        <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
          <ClosureCelebration xp={problem.xp} microSkill={problem.micro_skill} />
        </div>
      ) : (
        <>
          {/* Интро: почти финал — закрепим, что разобрали */}
          <section
            className="ap-card reveal flex items-start gap-3 p-4"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <Mascot mood="cheer" size={64} className="-mt-1 shrink-0" />
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="text-caption1-medium uppercase tracking-[0.12em] text-text-brand">
                Закрепление · {problem.topic_label}
              </span>
              <h1 className="text-h2 text-text-primary">Последний шаг</h1>
              <p className="text-caption1 text-text-primary">
                Реши похожую сам — без подсказок. Получится — ошибка закрыта.
              </p>
            </div>
          </section>

          <div className="reveal" style={{ '--reveal-delay': '120ms' } as CSSProperties}>
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
    </div>
  )
}
