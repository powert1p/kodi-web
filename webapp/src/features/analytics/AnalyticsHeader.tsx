import { Mascot } from '../../components/Mascot'

interface AnalyticsHeaderProps {
  /** Сколько типов ошибок в списке (для строки-сводки). */
  total: number
}

// Шапка «Прогресс»: Кёди (think — «смотрит» на топ-ошибку) + заголовок +
// одна growth-mindset строка. Тон: ошибка = «где растёт мозг», без наказания.
export function AnalyticsHeader({ total }: AnalyticsHeaderProps) {
  return (
    <section className="card-flat flex items-start gap-3 rounded-(--radius-card) p-4">
      <Mascot mood="think" size={64} className="-mt-1 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[0.66rem] font-extrabold uppercase tracking-[0.16em] text-primary-ink">
          Прогресс
        </span>
        <h1 className="font-display text-[1.5rem] font-black leading-[1.05] tracking-tight text-ink">
          Твои частые ошибки
        </h1>
        <p className="text-sm font-bold leading-snug text-ink">
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
