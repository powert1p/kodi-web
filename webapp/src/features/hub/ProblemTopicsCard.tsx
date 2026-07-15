import type { CSSProperties } from 'react'
import { useProblemTopics } from '../../lib/api'

interface ProblemTopicsCardProps { delay?: number }

export function ProblemTopicsCard({ delay = 0 }: ProblemTopicsCardProps) {
  const { data, isPending, isError } = useProblemTopics()
  if (isPending) return <ProblemTopicsSkeleton delay={delay} />
  if (isError || !data || data.length === 0) return null
  const topics = [...data].sort((a, b) => b.error_count - a.error_count).slice(0, 5)

  return (
    <section
      className="reveal rounded-card border border-ink/10 border-t-4 border-t-brand bg-surface p-5 shadow-lift-sm"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
      aria-labelledby="photo-topics-title"
    >
      <p className="text-mark text-brand-deep">По фото-разборам</p>
      <h2 id="photo-topics-title" className="mt-3 text-h3 text-ink">Где сбой повторялся</h2>
      <p className="mt-2 text-caption1 text-muted">Только наблюдения по фотографиям решений, не mastery темы.</p>
      <ol className="mt-5 border-t border-stroke">
        {topics.map((topic, index) => {
          const checked = Math.round(topic.closure_progress * 100)
          return (
            <li key={topic.topic_id} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-3 border-b border-stroke py-4">
              <span className="font-num text-caption1-medium text-brand-deep" aria-hidden>{String(index + 1).padStart(2, '0')}</span>
              <div className="min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <span className="text-caption1-medium text-ink">{topic.name_ru ?? 'Эта тема'}</span>
                  <span className="font-num shrink-0 text-caption1 text-muted">{topic.error_count}×</span>
                </div>
                <p className="mt-1 text-caption2 text-muted">контрольной подтверждено: {checked}%</p>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

function ProblemTopicsSkeleton({ delay }: { delay: number }) {
  return (
    <div
      className="reveal rounded-card border border-ink/10 border-t-4 border-t-paper-3 bg-surface p-5 shadow-lift-sm"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
      aria-busy="true"
      aria-label="Загрузка тем из фото-разборов"
    >
      <div className="shimmer h-3 w-32 bg-paper-2" />
      <div className="shimmer mt-4 h-7 w-48 bg-paper-2" />
      {[0, 1, 2].map((item) => <div key={item} className="mt-4 h-10 border-t border-stroke pt-4"><div className="shimmer h-4 w-full bg-paper-2" /></div>)}
    </div>
  )
}
