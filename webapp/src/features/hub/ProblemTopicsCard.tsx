import type { CSSProperties } from 'react'
import { useProblemTopics } from '../../lib/api'
import { ApLinearProgress } from '../../components/ApLinearProgress'
import { ApTag } from '../../components/ApTag'

interface ProblemTopicsCardProps {
  /** Задержка stagger-reveal в мс (позиция в общей ленте hub). */
  delay?: number
}

// Блок «Мои проблемные темы» (AiPlus ap-card) — над списком «Твои ошибки»:
// тема → бейдж числа ошибок → полоса прогресса закрытия. Сортировка по
// error_count убывающая (самая горящая тема сверху), топ-1 получает единственный
// на всю карточку тёплый акцент (ApTag primary «Начни отсюда») — то же зерно,
// что и warm-подложка HubHero, но не повторяем её целиком, только точечно.
// Error/empty — тихо скрываем блок (пока темы не посчитаны, лишний шум хуже пустоты).
export function ProblemTopicsCard({ delay = 0 }: ProblemTopicsCardProps) {
  const { data, isPending, isError } = useProblemTopics()

  if (isPending) return <ProblemTopicsSkeleton delay={delay} />
  if (isError || !data || data.length === 0) return null

  const topics = [...data]
    .sort((a, b) => b.error_count - a.error_count)
    .slice(0, 5)

  return (
    <section
      className="ap-card reveal flex flex-col gap-3 p-4"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-center gap-2">
        <h2 className="text-h3 text-text-primary">Мои проблемные темы</h2>
        <span className="ml-auto text-caption1 text-text-secondary">закрой ошибки</span>
      </div>

      <ul className="flex flex-col gap-3.5">
        {topics.map((t, i) => {
          const pct = Math.round(t.closure_progress * 100)
          const name = t.name_ru ?? t.topic_id
          const isTop = i === 0

          return (
            <li key={t.topic_id} className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-caption1-medium text-text-primary">
                  {name}
                </span>
                {isTop && <ApTag status="primary">Начни отсюда</ApTag>}
                <span className="font-num inline-flex h-[18px] min-w-[18px] shrink-0 items-center justify-center rounded-full bg-bg-secondary px-1.5 text-caption2-medium tabular-nums text-text-dark-gray">
                  {t.error_count}
                </span>
              </div>
              <ApLinearProgress
                value={pct}
                max={100}
                minShown={0.02}
                ariaLabel={`Закрытие темы «${name}»: ${pct}%`}
              />
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// Loading: каркас той же формы (шапка + 2 строки тема/полоса), чтобы карточка
// не «прыгала» при появлении данных — тот же shimmer, что и в HubSkeleton.
function ProblemTopicsSkeleton({ delay }: { delay: number }) {
  return (
    <div
      className="ap-card reveal flex flex-col gap-3 p-4"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
      aria-busy="true"
      aria-label="Загрузка проблемных тем"
    >
      <div className="shimmer h-5 w-48 rounded-sm bg-bg-secondary" />
      {[0, 1].map((i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <div className="shimmer h-4 w-32 rounded-sm bg-bg-secondary" />
            <div className="shimmer ml-auto h-[18px] w-7 rounded-full bg-bg-secondary" />
          </div>
          <div className="shimmer h-2 w-full rounded-xs bg-bg-secondary" />
        </div>
      ))}
    </div>
  )
}
