import type { CSSProperties } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { LeftIcon } from '../../icons'
import { RouteMeter } from '../../components/route/RouteMeter'
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
  const location = useLocation()
  const { taskId } = useParams<{ taskId: string }>()
  const { data: task, isLoading: isTaskLoading } = useWrongTask(taskId ?? '')
  const closure = useClosure(task?.problem_id ?? 0, task?.primary_micro_skill ?? null)

  // DEV-механизм показа кульминации для рендера/панели (прод-поведение НЕ меняется —
  // гейт import.meta.env.DEV, в проде всегда false): ?dev=celebrate форсит празднование.
  const devCelebrate =
    import.meta.env.DEV && new URLSearchParams(location.search).get('dev') === 'celebrate'

  const isDone = closure.status === 'correct' || devCelebrate
  const problem = closure.problem

  // Задача не найдена в кэше wrong-tasks (id устарел/не существует) — не висим
  // вечно на "Готовлю контрольную…", а показываем информер с выходом на срез.
  const isTaskNotFound = !isTaskLoading && !task

  // Финальный подъём: честное число пройденных ступеней лесенки (clamp 3-6 для полосы).
  const climb = Math.min(Math.max(task?.steps.length ?? 4, 3), 6)

  return (
    <div className="flex min-h-[calc(100dvh-8rem)] flex-col gap-4">
      {/* Назад к срезу — тихая ghost-кнопка (ambient-навигация, не state-CTA) */}
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <ApButton variant="ghost" size="m" onClick={() => navigate('/')} className="self-start">
          <LeftIcon size={16} />
          К срезу
        </ApButton>
      </div>

      {/* Короткий экран. Кульминация/ошибка — центрируем в высоте (canon §2.8);
          рабочий экран закрепления — top-align, чтобы верх не пустовал (R3 §4). */}
      {isTaskNotFound ? (
        <div className="flex flex-1 flex-col justify-center">
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
        </div>
      ) : isDone ? (
        <div
          className="reveal flex flex-1 flex-col justify-center"
          style={{ '--reveal-delay': '60ms' } as CSSProperties}
        >
          <ClosureCelebration xp={problem?.xp ?? 30} />
        </div>
      ) : (
        <>
          {/* Финальный подъём — участок маршрута к вершине (§1 сигнатура сквозная +
              §4 якорь первого вьюпорта): держит ВЕРХ экрана. */}
          <div
            className="reveal flex flex-col gap-2"
            style={{ '--reveal-delay': '40ms' } as CSSProperties}
          >
            <p className="font-display text-caption1-medium uppercase tracking-[0.12em] text-brand-ink">
              Финальный подъём — вершина близко
            </p>
            <RouteMeter current={climb} total={climb} ariaLabel="Финальный подъём к вершине" />
          </div>

          {/* Интро + контрольная центрируются в ОСТАВШЕЙСЯ высоте — низ не оседает
              мёртвой третью (R4 §2), маршрут выше держит верх. */}
          <div className="flex flex-1 flex-col justify-center gap-4">
            {/* Интро: почти финал. Подводка к ЕДИНСТВЕННОЙ активной карточке (контрольная). */}
            <section
              className="reveal flex items-start gap-3"
              style={{ '--reveal-delay': '80ms' } as CSSProperties}
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

            <div className="reveal" style={{ '--reveal-delay': '140ms' } as CSSProperties}>
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
          </div>
        </>
      )}
    </div>
  )
}
