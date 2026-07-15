import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { FocusTopbar } from '../../components/FocusTopbar'
import { HubError } from '../hub/HubError'
import { SrezHeader } from './SrezHeader'
import { SrezQuestionCard } from './SrezQuestionCard'
import { SrezFeedback } from './SrezFeedback'
import { SrezSkeleton } from './SrezSkeleton'
import { SrezEmpty } from './SrezEmpty'
import { SrezFinal } from './SrezFinal'
import { useSrez } from './useSrez'

export function SrezPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const srez = useSrez()
  const [value, setValue] = useState('')

  useEffect(() => { setValue('') }, [srez.currentTask?.problem_id])

  if (srez.isLoading) return <FocusState><SrezSkeleton /></FocusState>
  if (srez.isError) return <FocusState><HubError onRetry={srez.refetch} title="Мини-срез не загрузился" text="Проверь интернет и повтори. Новая выборка начнётся только после успешной загрузки." /></FocusState>
  if (srez.tasks.length === 0) return <FocusState><SrezEmpty /></FocusState>
  if (srez.finished) {
    return (
      <FocusState wide>
        <SrezFinal wrongCount={srez.wrongCount} onContinue={() => {
          void queryClient.invalidateQueries({ queryKey: ['wrong-tasks'] })
          navigate('/')
        }} />
      </FocusState>
    )
  }

  const task = srez.currentTask
  if (!task) return null
  const locked = srez.phase === 'feedback' || srez.submitting

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!value.trim() || locked) return
    srez.submit(value)
  }

  return (
    <div className="min-h-dvh bg-paper">
      <FocusTopbar />
      <div className="mx-auto flex min-h-[calc(100dvh-4.5rem)] max-w-4xl items-start px-4 py-3 md:items-center md:px-8 md:py-8">
        <section className="w-full min-w-0" aria-label="Вопрос мини-среза">
          <SrezHeader current={task.position} total={task.total} />
          <div className="min-w-0">
            <form onSubmit={submit} className="min-w-0">
              <SrezQuestionCard topic={task.node_title} statement={task.statement} answerType={task.answer_type} value={value} disabled={locked} onChange={setValue} />
              {srez.answerError && (
                <ApInformer tone="attn" role="alert" className="mt-5 max-w-3xl">
                  <span className="text-study">Связь прервалась. Ответ остался в поле — попробуй ещё раз.</span>
                </ApInformer>
              )}
              {srez.phase === 'answering' && (
                <ApButton type="submit" size="l" loading={srez.submitting} disabled={!value.trim() || locked} className="mt-4 w-full sm:w-auto sm:min-w-56">
                  Проверить
                </ApButton>
              )}
            </form>
            {srez.phase === 'feedback' && srez.feedbackCorrect !== null && (
              <div className="mt-5 flex max-w-3xl flex-col gap-3" aria-live="polite">
                <SrezFeedback correct={srez.feedbackCorrect} />
                <ApButton size="l" onClick={srez.next}>Следующий вопрос</ApButton>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function FocusState({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-dvh bg-paper">
      <FocusTopbar />
      <div className={['mx-auto flex min-h-[calc(100dvh-5rem)] items-center px-5 py-10', wide ? 'max-w-5xl' : 'max-w-3xl'].join(' ')}>{children}</div>
    </div>
  )
}
