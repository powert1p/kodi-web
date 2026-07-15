import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import type { LearningResult } from '../../lib/types'

export function LearningResultView({ result }: { result: LearningResult }) {
  const navigate = useNavigate()
  return (
    <section className="tape-stage tape-stage--success reveal px-5 py-7 md:px-10 md:py-11" aria-labelledby="learning-result-title">
      <p className="text-mark text-success">Урок завершён · результат сохранён</p>
      <h1 id="learning-result-title" tabIndex={-1} className="mt-4 max-w-3xl text-h1 text-ink focus-visible:outline-none">
        {result.title}
      </h1>
      <p className="mt-5 max-w-3xl text-study text-text">{result.skill}</p>

      <p className="proof-rule mt-7 max-w-2xl text-title text-ink">{result.evidence_label}</p>

      <dl className="mt-7 grid gap-3 sm:grid-cols-3">
        <div className="rounded-control bg-sage-soft px-4 py-4">
          <dd className="font-display text-h2 text-ink">{result.independent_completed}</dd>
          <dt className="mt-1 text-caption1-medium text-muted">самостоятельных задания</dt>
        </div>
        <div className="rounded-control bg-sage-soft px-4 py-4">
          <dd className="font-display text-h2 text-ink">{result.transfer_completed}</dd>
          <dt className="mt-1 text-caption1-medium text-muted">задача на перенос</dt>
        </div>
        <div className="rounded-control bg-paper-2 px-4 py-4">
          <dd className="font-display text-h2 text-ink">{result.without_support} из {result.independent_completed}</dd>
          <dt className="mt-1 text-caption1-medium text-muted">с первого раза без опоры</dt>
        </div>
      </dl>

      <div className="mt-8 flex justify-end border-t border-ink/10 pt-6">
        <ApButton size="l" full onClick={() => navigate('/')} className="sm:w-auto">
          Вернуться в путь
        </ApButton>
      </div>
    </section>
  )
}
