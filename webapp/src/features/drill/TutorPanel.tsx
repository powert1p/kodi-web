import { useEffect, useRef, useState } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApInformer } from '../../components/ApInformer'
import { LongArrowRightIcon } from '../../icons'
import { sendTutorMessage, ApiError } from '../../lib/api'
import type { TutorMessage } from '../../lib/types'

interface TutorPanelProps {
  problemId: number
  decompIdx?: number | null
}

// Локальное приветствие — рендерится сразу, без обращения к ИИ (не жжём лимит на открытие).
const GREETING = 'Давай разберёмся вместе. Что именно непонятно?'

// Чат-тьютор после диагноза (AiPlus ap-card): ученик спрашивает — Кёди наводит,
// не раскрывая финальный ответ. История — авторитетная с сервера (setHistory(res.history)),
// но неотправленное/упавшее сообщение держим локально в `pending`, чтобы при ошибке
// не терять текст ученика и дать «Повторить» тем же сообщением.
export function TutorPanel({ problemId, decompIdx }: TutorPanelProps) {
  const [history, setHistory] = useState<TutorMessage[]>([])
  const [pending, setPending] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'sending' | 'error'>('idle')
  const [errorText, setErrorText] = useState('')
  const [input, setInput] = useState('')

  const scrollRef = useRef<HTMLDivElement>(null)

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
      const res = await sendTutorMessage(problemId, message, decompIdx)
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
    <article className="ap-card reveal flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <Mascot mood="think" size={32} className="shrink-0" />
        <span className="text-caption1-medium text-text-primary">Спроси Кёди про этот шаг</span>
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
        <ApInformer
          type="warning"
          role="alert"
          leading={<span className="text-sm leading-none">🌱</span>}
        >
          <div className="flex flex-col items-start gap-2">
            <span>{errorText}</span>
            <ApButton
              variant="outlined"
              size="s"
              className="min-h-11"
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
          placeholder="Например: почему тут не 20?"
          className="min-h-11 flex-1 resize-none rounded-lg border border-stroke-primary-disabled bg-bg-primary px-3 py-2.5 text-caption1 text-text-primary outline-none transition-colors placeholder:text-text-secondary focus:border-[1.5px] focus:border-stroke-brand disabled:bg-bg-disabled disabled:text-text-disabled"
        />
        <button
          type="button"
          aria-label="Отправить"
          disabled={status === 'sending' || input.trim().length === 0}
          onClick={submitInput}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-bg-brand text-text-tertiary transition-colors hover:bg-bg-brand-hovered disabled:bg-bg-disabled disabled:text-text-disabled"
        >
          <LongArrowRightIcon size={20} className={status === 'sending' ? 'animate-spin' : ''} />
        </button>
      </div>
    </article>
  )
}

// Пузырь реплики: ученик справа (тёплая бренд-заливка — «это моё»),
// тьютор слева (белый приподнятый чип на фоне ap-card — «это ответили мне»).
function Bubble({ role, children }: { role: 'user' | 'assistant'; children: string }) {
  const isUser = role === 'user'
  return (
    <p
      className={[
        'max-w-[85%] text-caption1 text-text-primary',
        isUser
          ? 'self-end rounded-2xl rounded-br-sm bg-bg-brand-disabled px-3 py-2'
          : 'self-start rounded-2xl rounded-bl-sm border border-stroke-secondary bg-bg-primary px-3 py-2',
      ].join(' ')}
    >
      {children}
    </p>
  )
}

// Индикатор «печатает» — три точки с волной, честная замена ответу на время sending.
function TypingBubble() {
  return (
    <div className="flex w-fit items-center gap-1 self-start rounded-2xl rounded-bl-sm border border-stroke-secondary bg-bg-primary px-3 py-2.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-secondary motion-reduce:animate-none"
          style={{ animationDelay: `${i * 120}ms` }}
        />
      ))}
    </div>
  )
}
