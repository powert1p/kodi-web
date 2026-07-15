import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { MathText } from '../../components/MathText'
import { LongArrowRightIcon } from '../../icons'

interface ClosureCelebrationProps {
  statement: string | null
  answer: string | null
  topic: string
}

export function ClosureCelebration({ statement, answer, topic }: ClosureCelebrationProps) {
  const navigate = useNavigate()
  return (
    <section className="equation-commit mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-6xl items-center gap-6 px-4 py-5 md:px-8 lg:grid-cols-[minmax(0,1.12fr)_minmax(19rem,0.7fr)] lg:py-8">
      <div className="tape-card min-w-0 px-6 py-8 md:px-10 md:py-10">
        <p className="text-mark text-success-ink">Подтверждено на новой задаче · {topic}</p>
        {statement && (
          <div className="math-prose mt-5 pb-2">
            <p className="formula-body max-w-4xl text-[clamp(27px,4vw,42px)] font-semibold leading-[1.12] tracking-[-0.04em] text-ink">
              <MathText text={statement} />
            </p>
          </div>
        )}
        <p className="font-display mt-7 text-[clamp(42px,9vw,76px)] font-semibold leading-none text-ink">
          Ответ = <span className="bracket-slot" data-state="done">{answer ?? '✓'}</span>
        </p>
        <div className="mt-7 flex items-center gap-3" aria-hidden>
          <span className="grid size-8 place-items-center rounded-full bg-success text-surface">✓</span>
          <span className="h-1 flex-1 rounded-full bg-success" />
          <span className="grid size-8 place-items-center rounded-full bg-brand text-ink">→</span>
        </div>
      </div>

      <div className="grid overflow-hidden rounded-card border border-ink/10 bg-sage-soft/60 shadow-lift-sm">
        <div className="px-6 pt-7 md:px-8">
          <p className="text-mark text-success-ink">Ход решения восстановлен</p>
          <h1 className="mt-3 text-h2 text-ink">Получилось самостоятельно.</h1>
          <p className="mt-3 text-body text-text">Это уже не память ответа — ты перенёс способ на новую задачу.</p>
          <ApButton className="mt-5 w-full" size="l" onClick={() => navigate('/')}>
            К моему пути <LongArrowRightIcon size={18} />
          </ApButton>
        </div>
        <Mascot mood="celebrate" size="xl" className="mt-3 h-52" />
      </div>
    </section>
  )
}
