import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'

// Empty: ни одной повторяющейся ошибки — это отличный знак. Празднично, одна строка + CTA.
export function AnalyticsEmpty() {
  const navigate = useNavigate()

  return (
    <div className="card-flat reveal flex flex-col items-center gap-5 rounded-(--radius-card) px-6 py-12 text-center">
      <Mascot mood="celebrate" size={104} className="bob" />
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-2xl font-black text-ink">
          Пока ошибок нет 🎉
        </h2>
        <p className="max-w-[17rem] text-sm font-semibold text-ink-mute">
          Отличный знак — повторяющихся промахов не накопилось. Решай дальше, и
          здесь будет видно, где растёт мозг.
        </p>
      </div>
      <Button3D variant="primary" size="lg" onClick={() => navigate('/')}>
        К срезу
      </Button3D>
    </div>
  )
}
