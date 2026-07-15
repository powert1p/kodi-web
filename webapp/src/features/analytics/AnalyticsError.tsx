import { ApButton } from '../../components/ApButton'
import { RestartIcon } from '../../icons'

interface AnalyticsErrorProps { onRetry: () => void }

export function AnalyticsError({ onRetry }: AnalyticsErrorProps) {
  return (
    <section className="tape-card reveal mx-auto mt-12 max-w-3xl px-6 py-9">
      <p className="text-mark text-oxide">Связь прервалась</p>
      <h1 className="mt-4 text-h2 text-ink">Прогресс не загрузился.</h1>
      <p className="mt-4 max-w-xl text-study text-text">Проверь интернет и попробуй ещё раз.</p>
      <ApButton className="mt-6" onClick={onRetry}><RestartIcon size={18} /> Повторить</ApButton>
    </section>
  )
}
