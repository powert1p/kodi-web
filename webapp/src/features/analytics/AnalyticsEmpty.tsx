import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'

export function AnalyticsEmpty() {
  const navigate = useNavigate()
  return (
    <section className="tape-card reveal mx-auto mt-12 max-w-3xl px-6 py-9">
      <p className="text-mark text-brand-deep">Прогресс</p>
      <h1 className="mt-4 text-h2 text-ink">Повторений пока не видно.</h1>
      <p className="mt-4 max-w-xl text-study text-text">Данных ещё мало или один тип сбоя пока не повторялся. Текущий учебный блок остаётся главным ориентиром.</p>
      <ApButton className="mt-6" onClick={() => navigate('/')}>К моему пути</ApButton>
    </section>
  )
}
