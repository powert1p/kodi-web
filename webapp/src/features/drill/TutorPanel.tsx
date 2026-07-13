import { useEffect, useRef, useState } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { ApCard } from '../../components/ApCard'
import { LongArrowRightIcon } from '../../icons'
import { sendTutorMessage, ApiError } from '../../lib/api'
import { track } from '../../lib/telemetry'
import type { TutorMessage } from '../../lib/types'

interface TutorPanelProps {
  problemId: number
  decompIdx?: number | null
  /** Ступень лесенки, на которой застрял ученик — бэк фокусирует диалог на ней. */
  stepN?: number | null
}

// Локальное приветствие — рендерится сразу, без обращения к ИИ (не жжём лимит на открытие).
const GREETING = 'Давай разберёмся вместе. Что именно непонятно?'

// Чат-тьютор после диагноза (AiPlus ap-card): ученик спрашивает — Кёди наводит,
// не раскрывая финальный ответ. История — авторитетная с сервера (setHistory(res.history)),
// но неотправленное/упавшее сообщение держим локально в `pending`, чтобы при ошибке
// не терять текст ученика и дать «Повторить» тем же сообщением.
export function TutorPanel({ problemId, decompIdx, stepN }: TutorPanelProps) {
  const [history, setHistory] = useState<TutorMessage[]>([])
  const [pending, setPending] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'sending' | 'error'>('idle')
  const [errorText, setErrorText] = useState('')
  const [input, setInput] = useState('')

  const scrollRef = useRef<HTMLDivElement>(null)

  // Телеметрия открытия панели тьютора — один раз за монтирование.
  const openTrackedRef = useRef(false)
  useEffect(() => {
    if (!openTrackedRef.current) {
      openTrackedRef.current = true
      void track('tutor_opened')
    }
  }, [])

  // Автоскролл к последней реплике при любом изменении переписки.
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [history, pending, status])

  async function send(message: string) {
    if (!message || status === 'sending') return
    setPending(message)
    setStatus('sending')
    try {
      const res = await sendTutorMessage(problemId, message, decompIdx, stepN)
      setHistory(res.history)
      setPending(null)
      setStatus('idle')
    } catch (err) {
      setErrorText(
        err instanceof ApiError && err.status === 429
          ? 'Слишком много вопросов подряд — подожди минуту.'
          : 'Кёди задумался и не расслышал. Попробуй ещё раз.'
      )
      setStatus('error')
    }
  }

  function submitInput() {
    const msg = input.trim()
    if (!msg) return
    setInput('')
    void send(msg)
  }

  return (
    <ApCard as="article" padding="m" className="reveal flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Mascot mood="thinking" size="s" className="shrink-0" />
        <span className="text-caption1-medium text-ink">Спроси Кёди про этот шаг</span>
      </div>

      <div
        ref={scrollRef}
        className="flex max-h-72 flex-col gap-2 overflow-y-auto scroll-smooth pr-0.5"
      >
        <Bubble role="assistant">{GREETING}</Bubble>
        {history.map((m, i) => (
          <Bubble key={i} role={m.role}>
            {m.content}
          </Bubble>
        ))}
        {pending && <Bubble role="user">{pending}</Bubble>}
        {status === 'sending' && <TypingBubble />}
      </div>

      {status === 'error' && (
        <ApInformer tone="attn" role="alert" leading={<span className="text-sm leading-none">🌱</span>}>
          <div className="flex flex-col items-start gap-2">
            <span>{errorText}</span>
            <ApButton
              variant="secondary"
              size="m"
              onClick={() => pending && void send(pending)}
            >
              Повторить
            </ApButton>
          </div>
        </ApInformer>
      )}

      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submitInput()
            }
          }}
          rows={1}
          disabled={status === 'sending'}
          placeholder="Например: с чего начать?"
          className="min-h-11 flex-1 resize-none rounded-control border border-stroke bg-surface px-3 py-3 text-caption1 text-text outline-none transition-colors placeholder:text-muted focus:border-[1.5px] focus:border-brand disabled:bg-stroke disabled:text-muted"
        />
        <button
          type="button"
          aria-label="Отправить"
          disabled={status === 'sending' || input.trim().length === 0}
          onClick={submitInput}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control bg-brand text-on-brand transition-colors hover:bg-brand-deep disabled:bg-stroke disabled:text-muted"
        >
          <LongArrowRightIcon size={20} className={status === 'sending' ? 'animate-spin' : ''} />
        </button>
      </div>
    </ApCard>
  )
}

// Пузырь реплики: ученик справа (тёплая brand-soft подложка — «это моё», §6),
// Кёди слева (белый приподнятый чип — «это ответили мне»). Реплики Кёди — учебный
// текст ≥18px (§5); реплика ученика — body 16px.
function Bubble({ role, children }: { role: 'user' | 'assistant'; children: string }) {
  const isUser = role === 'user'
  return (
    <p
      className={[
        'max-w-[85%]',
        isUser
          ? 'self-end rounded-card rounded-br-chip bg-brand-soft px-3 py-2 text-body text-text'
          : 'self-start rounded-card rounded-bl-chip border border-stroke bg-surface px-3 py-2 text-study text-text',
      ].join(' ')}
    >
      {children}
    </p>
  )
}

// Индикатор «печатает» — три точки с волной, честная замена ответу на время sending.
function TypingBubble() {
  return (
    <div className="flex w-fit items-center gap-1 self-start rounded-card rounded-bl-chip border border-stroke bg-surface px-3 py-3">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted motion-reduce:animate-none"
          style={{ animationDelay: `${i * 120}ms` }}
        />
      ))}
    </div>
  )
}
