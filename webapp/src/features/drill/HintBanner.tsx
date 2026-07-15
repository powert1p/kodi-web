import { MathText } from '../../components/MathText'

interface HintBannerProps { text: string; variant?: 'hint' | 'easier' }

export function HintBanner({ text, variant = 'hint' }: HintBannerProps) {
  const easier = variant === 'easier'
  return (
    <aside className="reveal rounded-control border border-brand/20 border-l-4 border-l-brand bg-brand-soft/45 p-4 text-text" role="status">
      <p className="text-mark text-brand-deep">{easier ? 'Шаг попроще' : 'Намёк'}</p>
      <p className="formula-body mt-2 text-study"><MathText text={text} /></p>
    </aside>
  )
}
