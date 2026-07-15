interface SrezFeedbackProps { correct: boolean }

export function SrezFeedback({ correct }: SrezFeedbackProps) {
  return (
    <div className={['reveal rounded-control border border-l-4 p-4', correct ? 'border-success/25 border-l-success bg-success-soft' : 'border-attn/25 border-l-brand bg-attn-soft'].join(' ')} role="status">
      <p className={['text-mark', correct ? 'text-success-ink' : 'text-attn-ink'].join(' ')}>{correct ? 'Сошлось' : 'Оставим в плане'}</p>
      <p className="mt-2 text-study text-text">{correct ? 'Верно.' : 'Этот шаг разберём позже. Правильный ответ сейчас не показываем.'}</p>
    </div>
  )
}
