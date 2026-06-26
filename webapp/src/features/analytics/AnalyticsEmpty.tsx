import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'

// Empty: ни одной повторяющейся ошибки — это отличный знак. Празднично, одна строка + CTA.
export function AnalyticsEmpty() {
  const navigate = useNavigate()

  return (
    <div className="ap-card reveal flex flex-col items-center gap-5 px-6 py-12 text-center">
      <Mascot mood="celebrate" size={104} className="bob" />
      <div className="flex flex-col gap-1.5">
        <h2 className="text-h2 text-text-primary">Пока ошибок нет 🎉</h2>
        <p className="max-w-[17rem] text-caption1 text-text-secondary">
          Отличный знак — повторяющихся промахов не накопилось. Решай дальше, и
          здесь будет видно, где растёт мозг.
        </p>
      </div>
      <ApButton variant="filled" size="m" onClick={() => navigate('/')}>
        К срезу
      </ApButton>
    </div>
  )
}
