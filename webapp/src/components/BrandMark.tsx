import { Link } from 'react-router-dom'

interface BrandMarkProps {
  to?: string
  /** Сохраняется для API-совместимости; новый seed-mark работает на светлых плоскостях. */
  inverse?: boolean
  className?: string
}

export function BrandMark({ to = '/', className = '' }: BrandMarkProps) {
  return (
    <Link
      to={to}
      aria-label="AiPlus — к учёбе"
      className={['brand-signature', className].join(' ')}
    >
      <span className="brand-signature__seed" aria-hidden>
        <span>a</span>
        <span className="brand-signature__plus">+</span>
      </span>
      <span className="brand-signature__name" aria-hidden>AiPlus</span>
    </Link>
  )
}
