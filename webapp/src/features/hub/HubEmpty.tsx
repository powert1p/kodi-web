import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'

// Empty: всё разобрано — праздничное, ободряющее. Маскот празднует, одна строка + CTA.
export function HubEmpty() {
  const navigate = useNavigate()

  return (
    <div className="card-flat reveal flex flex-col items-center gap-5 rounded-(--radius-card) px-6 py-12 text-center">
      <Mascot mood="celebrate" size={104} className="bob" />
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-2xl font-black text-ink">
          Всё разобрано 🎉
        </h2>
        <p className="max-w-[16rem] text-sm font-semibold text-ink-mute">
          Ни одной незакрытой ошибки. Мозг сегодня прокачан — так держать!
        </p>
      </div>
      <Button3D variant="success" size="lg" onClick={() => navigate('/analytics')}>
        Посмотреть прогресс
      </Button3D>
    </div>
  )
}
