import { Mascot } from '../../components/Mascot'

interface AnalyticsHeaderProps {
  /** Сколько типов ошибок в списке (для строки-сводки). */
  total: number
}

// Шапка «Прогресс» (AiPlus ap-card): Кёди (think — «смотрит» на топ-ошибку) +
// заголовок + одна growth-mindset строка. Ошибка = «где растёт мозг», без наказания.
export function AnalyticsHeader({ total }: AnalyticsHeaderProps) {
  return (
    <section className="ap-card flex items-start gap-3 p-4">
      <Mascot mood="think" size={64} className="-mt-1 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-caption1-medium uppercase tracking-[0.12em] text-text-brand">
          Прогресс
        </span>
        <h1 className="text-h2 text-text-primary">Твои частые ошибки</h1>
        <p className="text-caption1 text-text-primary">
          {total} {plural(total)}, где мозг ещё растёт. Начни с верхней — закроешь
          её, остальные пойдут легче.
        </p>
      </div>
    </section>
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
