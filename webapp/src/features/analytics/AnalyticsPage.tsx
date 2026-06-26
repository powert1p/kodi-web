import type { CSSProperties } from 'react'
import { useAnalytics, asAnalyticsData } from '../../lib/api'
import { AnalyticsHeader } from './AnalyticsHeader'
import { ErrorBar } from './ErrorBar'
import { AnalyticsSkeleton } from './AnalyticsSkeleton'
import { AnalyticsEmpty } from './AnalyticsEmpty'
import { AnalyticsError } from './AnalyticsError'

// Analytics (/analytics) — «Прогресс» (вкладка нижней навигации, активна здесь).
// Топ повторяющихся типов ошибок ученика как чанковые горизонтальные полосы
// (длина = повторяемость), отсортированы по убыванию; #1 промотирован «в фокусе».
// Источник — useAnalytics() (mock-fallback в DEV). Состояния: loading/empty/error/success.
export function AnalyticsPage() {
  const { data, isPending, isError, refetch } = useAnalytics()

  if (isPending) return <AnalyticsSkeleton />
  if (isError) return <AnalyticsError onRetry={() => void refetch()} />

  const analytics = asAnalyticsData(data)
  const items = analytics
    ? [...analytics.error_types].sort((a, b) => b.count - a.count)
    : []

  if (items.length === 0) return <AnalyticsEmpty />

  const max = items[0]?.count ?? 1

  return (
    <div className="flex flex-col gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <AnalyticsHeader total={items.length} />
      </div>

      <ul className="flex flex-col gap-3">
        {items.map((item, i) => (
          <li key={item.micro_skill}>
            <ErrorBar
              item={item}
              ratio={item.count / max}
              rank={i + 1}
              delay={70 + i * 60}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
