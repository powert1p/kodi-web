import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'

// Empty: сервер не подобрал ни одной задачи для среза — нечего проверять
// прямо сейчас (не ошибка, поэтому маскот празднует, а не «упс»).
export function SrezEmpty() {
  const navigate = useNavigate()

  return (
    <ApCard padding="l" className="reveal flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="celebrate" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h2 text-ink">Пока нечего проверять</h2>
        <p className="max-w-[16rem] text-study text-text">
          Срез появится, когда наберётся из чего выбрать задачи.
        </p>
      </div>
      <ApButton variant="primary" size="m" onClick={() => navigate('/')}>
        На главную
      </ApButton>
    </ApCard>
  )
}
