import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'

// Empty: всё разобрано — праздничное, ободряющее. Маскот празднует, одна строка + CTA.
export function HubEmpty() {
  const navigate = useNavigate()

  return (
    <ApCard padding="l" className="reveal flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="celebrate" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h2 text-ink">Всё разобрано 🎉</h2>
        <p className="max-w-[16rem] text-study text-text">
          Ни одной незакрытой ошибки. Мозг сегодня прокачан — так держать!
        </p>
      </div>
      <ApButton variant="primary" size="m" onClick={() => navigate('/srez')}>
        Пройти мини-срез
      </ApButton>
    </ApCard>
  )
}
