import { useNavigate } from 'react-router-dom'
import { ApButton } from '../components/ApButton'

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-3xl items-center px-5 py-10">
      <section className="tape-card w-full px-6 py-9 md:px-9">
        <p className="font-display text-[clamp(58px,16vw,100px)] font-semibold leading-none tracking-[-0.07em] text-brand-deep">404</p>
        <h1 className="mt-5 text-h2 text-ink">Такого экрана нет.</h1>
        <p className="mt-4 text-study text-text">Вернись к актуальному плану — там следующий разбор.</p>
        <ApButton className="mt-6" onClick={() => navigate('/')}>К моему пути</ApButton>
      </section>
    </div>
  )
}
