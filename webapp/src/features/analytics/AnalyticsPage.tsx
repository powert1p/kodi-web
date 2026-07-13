import type { CSSProperties } from 'react'
import { useAnalytics, asAnalyticsData } from '../../lib/api'
import { AnalyticsHeader } from './AnalyticsHeader'
import { ErrorBar } from './ErrorBar'
import { AnalyticsSkeleton } from './AnalyticsSkeleton'
import { AnalyticsEmpty } from './AnalyticsEmpty'
import { AnalyticsError } from './AnalyticsError'
import { skillLabel } from '../drill/microSkillLabel'
import { RouteSpine, type RouteStop } from '../../components/route/RouteSpine'

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

  // Маршрут частых ошибок: каждый паттерн — отметка (ранг несёт узел рельса), #1 —
  // current «в фокусе», остальные впереди; флажок-цель «все закрыты» (§1 сигнатура
  // сквозная — тот же язык маршрута, что hub/drill/срез/closure).
  const stops: RouteStop[] = [
    ...items.map<RouteStop>((item, i) => ({
      key: item.micro_skill,
      state: i === 0 ? 'current' : 'todo',
      label: String(i + 1),
      content: (
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
      ),
    })),
    {
      key: 'goal',
      state: 'flag',
      content: (
        <div className="flex min-h-8 items-center">
          <span className="font-display text-caption1-medium text-brand-ink">
            Цель — закрыть все и обнулить список
          </span>
        </div>
      ),
    },
  ]

  return (
    // Короткий список (мало паттернов) — центрируем в доступной высоте, а не
    // оставляем мёртвую половину под ним (canon §2.8). С длинным списком
    // justify-center не мешает — контент сам заполняет контейнер сверху вниз.
    <div className="flex min-h-[calc(100dvh-8rem)] flex-col justify-center gap-4">
      <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
        <AnalyticsHeader total={items.length} />
      </div>

      <div className="reveal" style={{ '--reveal-delay': '40ms' } as CSSProperties}>
        <RouteSpine
          stops={stops}
          currentIndex={0}
          ariaLabel="Маршрут частых ошибок — сверху самая частая"
        />
      </div>
    </div>
  )
}
