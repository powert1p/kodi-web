import type { ReactNode } from 'react'
import { Mascot } from './Mascot'

type Mood = 'hi' | 'thinking' | 'celebrate' | 'oops'

interface KodiBubbleProps {
  mood?: Mood
  /** Метка-контекст над репликой (напр. «Уровень 1 · с нуля»). */
  level?: string
  size?: 's' | 'm'
  children: ReactNode
  className?: string
}

// Голос Кёди-хозяина (§7 Кёди-протокол): маскот + тёплый пузырь brand-soft (тинт
// голоса, не сильный оранж действия §8) с хвостиком к маскоту. Реплика — учебный
// текст ≥18px (§5). Один компонент на hub-hi / drill-thinking / srez-присутствие.
export function KodiBubble({ mood = 'hi', level, size = 'm', children, className = '' }: KodiBubbleProps) {
  return (
    <div className={['flex items-start gap-3', className].join(' ')}>
      <Mascot mood={mood} size={size} className="mascot-shadow shrink-0" />
      <div className="min-w-0 flex-1 rounded-card rounded-tl-chip border border-brand/25 bg-brand-soft p-3">
        {level && (
          <div className="font-display mb-1 text-caption1-medium text-brand-ink">{level}</div>
        )}
        <p className="text-study text-text">{children}</p>
      </div>
    </div>
  )
}
