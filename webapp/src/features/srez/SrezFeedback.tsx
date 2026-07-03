import type { CSSProperties } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApInformer } from '../../components/ApInformer'

interface SrezFeedbackProps {
  correct: boolean
}

// Фидбек по ответу (§5 голос Кёди): верно — тёплое «Верно!» (hi/success).
// Неверно — НИКОГДА «Ошибка»/красный, только мягкое «Разберём это потом»
// (oops/attn-амбер). Правильный ответ здесь и нигде на экране не показывается
// (§2.5) — задача просто уйдёт в разбор позже.
export function SrezFeedback({ correct }: SrezFeedbackProps) {
  return (
    <div className="reveal" style={{ '--reveal-delay': '0ms' } as CSSProperties}>
      <ApInformer
        tone={correct ? 'success' : 'attn'}
        leading={<Mascot mood={correct ? 'hi' : 'oops'} size="s" />}
        role="status"
      >
        <span className="text-study">{correct ? 'Верно!' : 'Разберём это потом'}</span>
      </ApInformer>
    </div>
  )
}
