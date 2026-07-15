import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { LongArrowRightIcon } from '../../icons'

interface FinishedCardProps { taskId: string }

export function FinishedCard({ taskId }: FinishedCardProps) {
  const navigate = useNavigate()
  return (
    <article className="tape-card equation-commit grid overflow-hidden md:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="flex flex-col justify-center px-6 py-10 md:px-10 md:py-12">
        <p className="text-mark text-success-ink">Лента собрана</p>
        <p className="font-display mt-6 text-[clamp(38px,9vw,68px)] font-semibold leading-none text-ink">
          Ход решения собран
        </p>
      </div>
      <div className="flex flex-col justify-center bg-sage-soft/60 p-6 md:p-8">
        <h2 className="text-h2 text-ink">Теперь — без подсказок.</h2>
        <p className="mt-4 text-study text-text">Новая задача проверит, восстановился ли сам ход решения.</p>
        <ApButton className="mt-6" size="l" full onClick={() => navigate(`/closure/${taskId}`)}>
          Закрепить <LongArrowRightIcon size={18} />
        </ApButton>
      </div>
    </article>
  )
}
