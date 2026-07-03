import { ApLinearProgress } from '../../components/ApLinearProgress'

interface SrezHeaderProps {
  /** Позиция текущей задачи (1-based, приходит с сервера). */
  current: number
  total: number
}

// Шапка среза: заголовок + счётчик «N из M» + тонкая полоса прогресса (brand).
// Без back-кнопки — срез короткий линейный проход, лишняя навигация не нужна.
export function SrezHeader({ current, total }: SrezHeaderProps) {
  return (
    <header className="flex flex-col gap-3 pt-1">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-h2 text-ink">Мини-срез</h1>
        <span className="font-num shrink-0 rounded-chip bg-surface px-3 py-1 text-caption2-medium tabular-nums text-text">
          {current} из {total}
        </span>
      </div>
      <ApLinearProgress
        value={total > 0 ? current / total : 0}
        minShown={0.04}
        ariaLabel={`Задача ${current} из ${total}`}
      />
    </header>
  )
}
