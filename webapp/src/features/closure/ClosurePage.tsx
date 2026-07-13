import type { CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { LeftIcon } from '../../icons'
import { VerificationCard } from './VerificationCard'
import { ClosureCelebration } from './ClosureCelebration'
import { useClosure } from './useClosure'
import { useWrongTask } from '../../lib/api'

// Closure (/closure/:taskId) — награда + проверка. После пройденной лесенки
// ученик решает контрольную на ТОТ ЖЕ навык (новые числа) БЕЗ подсказок.
// Верно → празднование + штамп «ЗАКРЫТО» + XP + «Дальше →» на Hub. Верный ответ
// сервер помечает recurring_errors.resolved. Состояния: loading/solving/wrong/error/correct.
export function ClosurePage() {
  const navigate = useNavigate()
  const { taskId } = useParams<{ taskId: string }>()
  const { data: task, isLoading: isTaskLoading } = useWrongTask(taskId ?? '')
  const closure = useClosure(task?.problem_id ?? 0, task?.primary_micro_skill ?? null)

  const isDone = closure.status === 'correct'
  const problem = closure.problem

  // Задача не найдена в кэше wrong-tasks (id устарел/не существует) — не висим
  // вечно на "Готовлю контрольную…", а показываем информер с выходом на срез.
  const isTaskNotFound = !isTaskLoading && !task

  return (
    <div className="flex min-h-[calc(100dvh-8rem)] flex-col gap-4">
      {/* Назад к срезу — тихая ghost-кнопка (ambient-навигация, не state-CTA) */}
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <ApButton variant="ghost" size="m" onClick={() => navigate('/')} className="self-start">
          <LeftIcon size={16} />
          К срезу
        </ApButton>
      </div>

      {/* Короткий экран (интро + одна контрольная) — центрируем группу в
          оставшейся высоте, а не оставляем мёртвую половину под ней (canon §2.8) */}
      <div className="flex flex-1 flex-col justify-center gap-4">
      {isTaskNotFound ? (
        <ApCard
          padding="m"
          className="reveal flex flex-col items-start gap-3"
          style={{ '--reveal-delay': '60ms' } as CSSProperties}
        >
          <p className="text-caption1 text-muted">
            Не нашли эту задачу — возможно, срез уже обновился.
          </p>
          <ApButton variant="secondary" size="m" onClick={() => navigate('/')}>
            К срезу
          </ApButton>
        </ApCard>
      ) : isDone ? (
        <div className="reveal" style={{ '--reveal-delay': '60ms' } as CSSProperties}>
          <ClosureCelebration xp={problem?.xp ?? 30} />
        </div>
      ) : (
        <>
          {/* Интро: почти финал — закрепим, что разобрали. Без карточки-рамки
              (canon §2.8/§4: меньше хрома, следующий блок выше) — это подводка
              к ЕДИНСТВЕННОЙ активной карточке (контрольная) ниже, не отдельный блок. */}
          <section
            className="reveal flex items-start gap-3"
            style={{ '--reveal-delay': '60ms' } as CSSProperties}
          >
            <Mascot mood="hi" size="m" className="mascot-shadow -mt-1 shrink-0" />
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="font-display text-caption1-medium uppercase tracking-[0.12em] text-brand-ink">
                Закрепление · {problem?.topic_label ?? task?.topic_label ?? ''}
              </span>
              <h1 className="text-h2 text-ink">Последний шаг</h1>
              <p className="text-study text-text">
                Реши похожую сам — без подсказок. Получится — ошибка закрыта.
              </p>
            </div>
          </section>

          <div className="reveal" style={{ '--reveal-delay': '120ms' } as CSSProperties}>
            {closure.status === 'error' ? (
              <ApCard padding="m" className="flex flex-col items-start gap-3">
                <p className="text-caption1 text-muted">
                  Не получилось загрузить контрольную. Попробуй ещё раз.
                </p>
                <ApButton variant="secondary" size="m" onClick={() => navigate('/')}>
                  К срезу
                </ApButton>
              </ApCard>
            ) : !problem || closure.status === 'loading' ? (
              <p className="text-caption1 text-muted">Готовлю контрольную…</p>
            ) : (
              <VerificationCard
                statement={problem.statement}
                wrong={closure.status === 'wrong'}
                attempts={closure.attempts}
                onCheck={closure.check}
                onResume={closure.resume}
              />
            )}
          </div>
        </>
      )}
      </div>
    </div>
  )
}
