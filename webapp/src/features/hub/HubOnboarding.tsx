import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'

export function HubOnboarding() {
  const navigate = useNavigate()
  return (
    <section className="tape-card grid overflow-hidden md:grid-cols-[minmax(0,1fr)_minmax(18rem,0.56fr)]">
      <div className="flex flex-col justify-center px-6 py-10 md:px-10 md:py-14">
        <p className="text-mark text-brand-deep">Первый шаг</p>
        <h1 className="mt-5 text-h1 text-ink">Узнаем, с чего начать.</h1>
        <p className="mt-5 max-w-xl text-study text-text">
          Ответь на несколько вопросов в своём темпе. После появится точный план разбора — без оценок и случайных задач.
        </p>
        <ApButton className="mt-7 w-full sm:w-auto sm:self-start" size="l" onClick={() => navigate('/srez')}>
          Начать мини-срез
        </ApButton>
      </div>
      <Mascot mood="hi" size="xl" eager className="min-h-72 bg-sage-soft/60 md:min-h-full" />
    </section>
  )
}
