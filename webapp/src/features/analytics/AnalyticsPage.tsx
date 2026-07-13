import type { CSSProperties } from 'react'
import { useAnalytics, asAnalyticsData } from '../../lib/api'
import { AnalyticsHeader } from './AnalyticsHeader'
import { ErrorBar } from './ErrorBar'
import { AnalyticsSkeleton } from './AnalyticsSkeleton'
import { AnalyticsEmpty } from './AnalyticsEmpty'
import { AnalyticsError } from './AnalyticsError'
import { skillLabel } from '../drill/microSkillLabel'

// Analytics (/analytics) — «Прогресс» (вкладка нижней навигации, активна здесь).
// Топ повторяющихся типов ошибок ученика как чанковые горизонтальные полосы
// (длина = повторяемость), отсортированы по убыванию; #1 промотирован «в фокусе».
// Источник — useAnalytics() → my_top (BE AnalyticsResponse). Состояния: loading/empty/error/success.
export function AnalyticsPage() {
  const { data, isPending, isError, refetch } = useAnalytics()

  if (isPending) return <AnalyticsSkeleton />
  if (isError) return <AnalyticsError onRetry={() => void refetch()} />

  const analytics = asAnalyticsData(data)
  const items = analytics
    ? [...analytics.my_top].sort((a, b) => b.error_count - a.error_count)
    : []

  if (items.length === 0) return <AnalyticsEmpty />

  const max = items[0]?.error_count ?? 1

  return (
    // Короткий список (мало паттернов) — центрируем в доступной высоте, а не
    // оставляем мёртвую половину под ним (canon §2.8). С длинным списком
    // justify-center не мешает — контент сам заполняет контейнер сверху вниз.
    <div className="flex min-h-[calc(100dvh-8rem)] flex-col justify-center gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <AnalyticsHeader total={items.length} />
      </div>

      <ul className="flex flex-col gap-3">
        {items.map((item, i) => (
          <li key={item.micro_skill}>
            <ErrorBar
              item={{
                micro_skill: item.micro_skill,
                // Внутренний код (canon §2 п.2) — никогда не в UI: нет русского
                // label_ru → нейтральное «Этот тип ошибок», не snake_case.
                label: item.label_ru ?? skillLabel(item.micro_skill) ?? 'Этот тип ошибок',
                topic_label: item.node_id ?? '',
                count: item.error_count,
                last_cause: item.last_cause_text,
              }}
              ratio={item.error_count / max}
              max={max}
              rank={i + 1}
              delay={70 + i * 60}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
