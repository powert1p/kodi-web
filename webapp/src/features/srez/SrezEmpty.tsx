import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'

export function SrezEmpty() {
  const navigate = useNavigate()
  return (
    <section className="tape-card reveal w-full px-6 py-8">
      <p className="text-mark text-brand-deep">Мини-срез</p>
      <h1 className="mt-4 text-h2 text-ink">Пока нечего проверять.</h1>
      <p className="mt-4 max-w-lg text-study text-text">Срез появится, когда наберётся достаточно подходящих задач.</p>
      <ApButton className="mt-6" onClick={() => navigate('/')}>К моему пути</ApButton>
    </section>
  )
}
