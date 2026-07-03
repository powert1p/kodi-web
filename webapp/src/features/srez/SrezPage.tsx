import { useEffect, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { Mascot } from '../../components/Mascot'
import { HubError } from '../hub/HubError'
import { SrezHeader } from './SrezHeader'
import { SrezQuestionCard } from './SrezQuestionCard'
import { SrezFeedback } from './SrezFeedback'
import { SrezSkeleton } from './SrezSkeleton'
import { SrezEmpty } from './SrezEmpty'
import { SrezFinal } from './SrezFinal'
import { useSrez } from './useSrez'

// /srez — мини-срез (Блок 1.0 «Пилот-подготовка»): 12 задач вразброс тем,
// правильность решает ТОЛЬКО сервер — клиент никогда не хранит и не
// показывает верный ответ (канон §2.5). Один экран — одна задача — один
// primary-CTA «Проверить»; фидбек — реплика Кёди (§5), авто-переход к
// следующей задаче. Финал — счётчик тем для разбора → назад на хаб.
export function SrezPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const srez = useSrez()
  const [value, setValue] = useState('')

  // Новая задача — очищаем поле (ответ прошлой задачи не переносится).
  useEffect(() => {
    setValue('')
  }, [srez.currentTask?.problem_id])

  // Короткие состояния (лоадер/ошибка/пусто/финал) центрируем в доступной высоте —
  // без этого под ними остаётся мёртвая нижняя половина вьюпорта (canon §2.8).
  if (srez.isLoading) {
    return <CenteredState><SrezSkeleton /></CenteredState>
  }
  if (srez.isError) {
    return <CenteredState><HubError onRetry={srez.refetch} /></CenteredState>
  }
  if (srez.tasks.length === 0) {
    return <CenteredState><SrezEmpty /></CenteredState>
  }

  if (srez.finished) {
    return (
      <CenteredState>
        <SrezFinal
          wrongCount={srez.wrongCount}
          onContinue={() => {
            void queryClient.invalidateQueries({ queryKey: ['wrong-tasks'] })
            navigate('/')
          }}
        />
      </CenteredState>
    )
  }

  const task = srez.currentTask
  if (!task) return null

  const locked = srez.phase === 'feedback' || srez.submitting

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!value.trim() || locked) return
    srez.submit(value)
  }

  return (
    // Top-align: карточка задачи начинается сразу под шапкой с прогрессом
    // (первый смысловой блок ≤96px от верха, canon §4) — без вертикального
    // центрирования, которое утапливало задачу в середину экрана.
    <div className="flex flex-col gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <SrezHeader current={task.position} total={task.total} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="reveal flex flex-col gap-4"
        style={{ '--reveal-delay': '80ms' } as CSSProperties}
      >
        <SrezQuestionCard
          topic={task.node_title}
          statement={task.statement}
          value={value}
          disabled={locked}
          onChange={setValue}
        />

        {srez.answerError && (
          <ApInformer tone="attn" leading={<Mascot mood="oops" size="s" />} role="alert">
            <span className="text-study">Не получилось проверить — попробуй ещё раз.</span>
          </ApInformer>
        )}

        <ApButton
          type="submit"
          variant="primary"
          size="l"
          full
          loading={srez.submitting}
          disabled={!value.trim() || locked}
        >
          Проверить
        </ApButton>
      </form>

      {srez.phase === 'feedback' && srez.feedbackCorrect !== null && (
        <SrezFeedback correct={srez.feedbackCorrect} />
      )}
    </div>
  )
}

// Центрирует короткий одиночный блок (лоадер/ошибка/пусто/финал) в доступной
// высоте экрана — тот же приём, что и активная задача (canon §2.8: без него
// под коротким контентом остаётся мёртвая нижняя половина вьюпорта).
function CenteredState({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[calc(100dvh-8rem)] flex-col justify-center">
      {children}
    </div>
  )
}
