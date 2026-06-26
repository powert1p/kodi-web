import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'

// Empty: всё разобрано — праздничное, ободряющее. Маскот празднует, одна строка + CTA.
export function HubEmpty() {
  const navigate = useNavigate()

  return (
    <div className="ap-card reveal flex flex-col items-center gap-5 px-6 py-12 text-center">
      <Mascot mood="celebrate" size={104} className="bob" />
      <div className="flex flex-col gap-1.5">
        <h2 className="text-h2 text-text-primary">Всё разобрано 🎉</h2>
        <p className="max-w-[16rem] text-caption1 text-text-secondary">
          Ни одной незакрытой ошибки. Мозг сегодня прокачан — так держать!
        </p>
      </div>
      <ApButton variant="filled" size="m" onClick={() => navigate('/analytics')}>
        Посмотреть прогресс
      </ApButton>
    </div>
  )
}
