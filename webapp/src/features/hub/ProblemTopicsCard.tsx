import type { CSSProperties } from 'react'
import { useProblemTopics } from '../../lib/api'
import { ApCard } from '../../components/ApCard'
import { ApLinearProgress } from '../../components/ApLinearProgress'
import { ApTag } from '../../components/ApTag'

interface ProblemTopicsCardProps {
  /** Задержка stagger-reveal в мс (позиция в общей ленте hub). */
  delay?: number
}

// Блок «Мои проблемные темы» (ApCard surface) — над списком «Твои ошибки»:
// тема → бейдж числа ошибок → полоса прогресса закрытия. Сортировка по
// error_count убывающая (самая горящая тема сверху), топ-1 получает единственный
// на всю карточку тёплый акцент (ApTag brand «Начни отсюда») — то же зерно,
// что и hero, но не повторяем её целиком, только точечно.
// Error/empty — тихо скрываем блок (пока темы не посчитаны, лишний шум хуже пустоты).
export function ProblemTopicsCard({ delay = 0 }: ProblemTopicsCardProps) {
  const { data, isPending, isError } = useProblemTopics()

  if (isPending) return <ProblemTopicsSkeleton delay={delay} />
  if (isError || !data || data.length === 0) return null

  const topics = [...data]
    .sort((a, b) => b.error_count - a.error_count)
    .slice(0, 5)

  return (
    <ApCard
      as="section"
      padding="m"
      className="reveal flex flex-col gap-3"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <h2 className="text-h3 text-ink">Мои проблемные темы</h2>

      <ul className="flex flex-col gap-4">
        {topics.map((t, i) => {
          const pct = t.closure_progress
          const name = t.name_ru ?? t.topic_id
          const isTop = i === 0

          return (
            <li key={t.topic_id} className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="line-clamp-2 min-w-0 flex-1 text-caption1-medium text-ink">
                  {name}
                </span>
                {isTop && <ApTag status="brand">Начни отсюда</ApTag>}
                <span className="font-num inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-paper px-1 text-caption2-medium tabular-nums text-text">
                  {t.error_count}
                </span>
              </div>
              <ApLinearProgress
                value={pct}
                minShown={0.02}
                ariaLabel={`Закрытие темы «${name}»: ${Math.round(pct * 100)}%`}
              />
            </li>
          )
        })}
      </ul>
    </ApCard>
  )
}

// Loading: каркас той же формы (шапка + 2 строки тема/полоса), чтобы карточка
// не «прыгала» при появлении данных — тот же shimmer, что и в HubSkeleton.
function ProblemTopicsSkeleton({ delay }: { delay: number }) {
  return (
    <ApCard
      padding="m"
      className="reveal flex flex-col gap-3"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
      aria-busy="true"
      aria-label="Загрузка проблемных тем"
    >
      <div className="shimmer h-5 w-48 rounded-chip bg-paper" />
      {[0, 1].map((i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="shimmer h-4 w-32 rounded-chip bg-paper" />
            <div className="shimmer ml-auto h-5 w-7 rounded-full bg-paper" />
          </div>
          <div className="shimmer h-2 w-full rounded-full bg-paper" />
        </div>
      ))}
    </ApCard>
  )
}
