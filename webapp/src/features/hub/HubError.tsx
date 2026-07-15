import { ApButton } from '../../components/ApButton'
import { RestartIcon } from '../../icons'

interface HubErrorProps {
  onRetry: () => void
  eyebrow?: string
  title?: string
  text?: string
}

export function HubError({
  onRetry,
  eyebrow = 'Связь прервалась',
  title = 'План не загрузился',
  text = 'Проверь интернет. Твой ответ и место в маршруте никуда не пропали.',
}: HubErrorProps) {
  return (
    <section className="tape-card reveal w-full px-6 py-8 md:px-8">
      <p className="text-mark text-oxide">{eyebrow}</p>
      <h1 className="mt-4 text-h2 text-ink">{title}</h1>
      <p className="mt-4 max-w-lg text-study text-text">{text}</p>
      <ApButton className="mt-6" onClick={onRetry}>
        <RestartIcon size={18} /> Повторить
      </ApButton>
    </section>
  )
}
