import { useAnalytics, asAnalyticsData } from '../../lib/api'
import { AnalyticsHeader } from './AnalyticsHeader'
import { ErrorBar } from './ErrorBar'
import { AnalyticsSkeleton } from './AnalyticsSkeleton'
import { AnalyticsEmpty } from './AnalyticsEmpty'
import { AnalyticsError } from './AnalyticsError'
import { skillLabel } from '../drill/microSkillLabel'

// Analytics (/analytics) — ранжированный список повторяющихся ошибок.
// Источник — useAnalytics() → my_top. Состояния: loading/empty/error/success.
export function AnalyticsPage() {
  const { data, isPending, isError, refetch } = useAnalytics()

  if (isPending) return <AnalyticsSkeleton />
  if (isError) return <AnalyticsError onRetry={() => void refetch()} />

  const analytics = asAnalyticsData(data)
  const items = analytics
    ? [...analytics.my_top].sort((a, b) => b.error_count - a.error_count)
    : []

  if (items.length === 0) return <AnalyticsEmpty />

  return (
    <div className="min-h-dvh bg-paper">
      <AnalyticsHeader total={items.length} />

      <section aria-labelledby="error-ranking-title" className="mx-auto max-w-[90rem] px-5 pb-12 md:px-8 lg:pb-16">
        <div className="flex items-end justify-between gap-4 border-b border-ink/20 pb-5">
          <div>
            <p className="text-mark text-brand-deep">По частоте</p>
            <h2 id="error-ranking-title" className="text-h3 text-ink">
              Сначала — самый частый сбой
            </h2>
          </div>
        </div>

        <ol>
          {items.map((item, i) => (
            <li key={item.micro_skill}>
              <ErrorBar
                item={{
                  micro_skill: item.micro_skill,
                  label: item.label_ru ?? skillLabel(item.micro_skill) ?? 'Этот тип ошибок',
                  topic_label: item.node_id ?? '',
                  count: item.error_count,
                  last_cause: item.last_cause_text,
                }}
                rank={i + 1}
                delay={70 + i * 60}
              />
            </li>
          ))}
        </ol>

        <p className="mt-8 max-w-2xl border-l-4 border-brand pl-4 text-caption1 text-muted">
          Список показывает накопленные повторения. Он не означает, что тема целиком не усвоена,
          и не обещает автоматическое исчезновение после одного ответа.
        </p>
      </section>
    </div>
  )
}
