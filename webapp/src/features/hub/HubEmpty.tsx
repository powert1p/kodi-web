import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'
import { HubOnboarding } from './HubOnboarding'

interface HubEmptyProps {
  /** Была ли у ученика активность. false → новичок (онбординг, БЕЗ праздника);
   *  true → ветеран, все ошибки закрыты (праздник). */
  hasActivity: boolean
}

// Два пустых состояния hub (§4 «empty»): развести новичка и ветерана —
// «Всё разобрано 🎉» бессмысленно для того, кто ещё ничего не решал.
export function HubEmpty({ hasActivity }: HubEmptyProps) {
  const navigate = useNavigate()

  // Новичок: тёплый онбординг вместо праздника.
  if (!hasActivity) return <HubOnboarding />

  // Ветеран: все ошибки закрыты — празднуем преодоление (Кёди-протокол §5 celebrate).
  return (
    <ApCard padding="l" className="flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="celebrate" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h2 text-ink">Всё разобрано 🎉</h2>
        <p className="max-w-[16rem] text-study text-text">
          Ни одной незакрытой ошибки. Мозг сегодня прокачан — так держать!
        </p>
      </div>
      <ApButton variant="primary" size="m" onClick={() => navigate('/srez')}>
        Пройти мини-срез ещё раз
      </ApButton>
    </ApCard>
  )
}
