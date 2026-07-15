import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { HubOnboarding } from './HubOnboarding'

interface HubEmptyProps { hasActivity: boolean }

export function HubEmpty({ hasActivity }: HubEmptyProps) {
  const navigate = useNavigate()
  if (!hasActivity) return <HubOnboarding />

  return (
    <section className="tape-card grid overflow-hidden md:grid-cols-[minmax(0,1fr)_minmax(18rem,0.52fr)]">
      <div className="flex flex-col justify-center px-6 py-10 md:px-10 md:py-14">
        <p className="text-mark text-success-ink">Очередь пустая</p>
        <h1 className="mt-5 text-h1 text-ink">Все задачи разобраны.</h1>
        <p className="mt-5 max-w-xl text-study text-text">
          Это не оценка всей темы — просто сейчас нет открытых мест сбоя. Новый мини-срез поможет найти следующий полезный шаг.
        </p>
        <ApButton className="mt-7 w-full sm:w-auto sm:self-start" size="l" onClick={() => navigate('/srez')}>
          Пройти мини-срез
        </ApButton>
      </div>
      <Mascot mood="celebrate" size="xl" className="min-h-72 bg-brand-soft/40 md:min-h-full" />
    </section>
  )
}
