import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'

// Empty: ни одной повторяющейся ошибки — это отличный знак. Празднично, одна строка + CTA.
export function AnalyticsEmpty() {
  const navigate = useNavigate()

  return (
    <ApCard padding="l" className="reveal flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="celebrate" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h2 text-ink">Пока ошибок нет 🎉</h2>
        <p className="max-w-[17rem] text-caption1 text-muted">
          Отличный знак — повторяющихся промахов не накопилось. Решай дальше, и
          здесь будет видно, где растёт мозг.
        </p>
      </div>
      <ApButton variant="primary" size="m" onClick={() => navigate('/')}>
        К срезу
      </ApButton>
    </ApCard>
  )
}
