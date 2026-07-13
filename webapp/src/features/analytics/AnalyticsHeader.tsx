import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'

interface AnalyticsHeaderProps {
  /** Сколько типов ошибок в списке (для строки-сводки). */
  total: number
}

// Шапка «Прогресс»: Кёди (thinking — «смотрит» на топ-ошибку) + заголовок +
// одна growth-mindset строка. Ошибка = «где растёт мозг», без наказания.
export function AnalyticsHeader({ total }: AnalyticsHeaderProps) {
  return (
    <ApCard as="section" padding="m" className="lift-sm flex items-start gap-3">
      <Mascot mood="thinking" size="m" className="mascot-shadow -mt-1 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-display text-caption1-medium uppercase tracking-[0.12em] text-brand-ink">
          Прогресс
        </span>
        <h1 className="text-h2 text-ink">Твои частые ошибки</h1>
        <p className="text-caption1 text-text">
          {total} {plural(total)}, где мозг ещё растёт. Начни с верхней — закроешь
          её, остальные пойдут легче.
        </p>
      </div>
    </ApCard>
  )
}

// Склонение «навык/паттерн» для русского счётчика.
function plural(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'паттерн'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'паттерна'
  return 'паттернов'
}
