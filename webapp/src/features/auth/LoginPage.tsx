// Экран входа / регистрации в Duolingo-стиле.
// Шаги: 1) ввод телефона → проверка /phone/check → ветка login или register.
//        2a) login: PIN → вход.
//        2b) register: имя → PIN → регистрация.
// Маскот приветствует, поддерживающий тон при ошибках (без «злого красного»).

import { useState, type FormEvent, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { Button3D } from '../../components/Button3D'
import { useAuth } from './AuthContext'
import { checkPhone } from '../../lib/auth'

// Этап формы.
type Step = 'phone' | 'login' | 'register-name' | 'register-pin'

// Маскот-настроение по этапу.
function mascotMood(step: Step, hasError: boolean) {
  if (hasError) return 'oops' as const
  if (step === 'phone') return 'cheer' as const
  if (step === 'login') return 'think' as const
  return 'celebrate' as const
}

// Заголовок по этапу.
function stepTitle(step: Step): string {
  if (step === 'phone') return 'Привет! Введи номер'
  if (step === 'login') return 'Добро пожаловать!'
  if (step === 'register-name') return 'Как тебя зовут?'
  return 'Придумай PIN'
}

// Подзаголовок по этапу.
function stepSub(step: Step, phone: string): string {
  if (step === 'phone') return 'Войдём через номер телефона'
  if (step === 'login') return `Введи PIN для ${phone}`
  if (step === 'register-name') return 'Имя видно только тебе'
  return 'Минимум 4 цифры — запомни его'
}

// Spinner для кнопки.
function Spinner() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      className="animate-spin"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeDasharray="31.4"
        strokeDashoffset="10"
        opacity="0.35"
      />
      <path
        d="M12 2 a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  )
}

// Поле ввода в стиле проекта.
interface FieldProps {
  label: string
  type?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  inputMode?: React.HTMLAttributes<HTMLInputElement>['inputMode']
  autoComplete?: string
  maxLength?: number
  disabled?: boolean
}

function Field({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  inputMode,
  autoComplete,
  maxLength,
  disabled,
}: FieldProps) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-display text-sm font-extrabold text-ink">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={inputMode}
        autoComplete={autoComplete}
        maxLength={maxLength}
        disabled={disabled}
        className={[
          'w-full rounded-(--radius-field) border-1.5 border-border bg-surface px-4',
          'text-base font-body font-semibold text-ink placeholder:text-ink-mute/60',
          'focus:border-primary-ink focus:outline-none',
          'disabled:opacity-50',
          'h-14',
        ].join(' ')}
        style={{ fontSize: '16px' }}
      />
    </label>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login, register } = useAuth()

  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const mood = mascotMood(step, !!error)

  // Сброс ошибки при изменении поля.
  function clearError() {
    if (error) setError(null)
  }

  // Обработчик шага «телефон».
  async function handlePhone(e: FormEvent) {
    e.preventDefault()
    const trimmed = phone.trim()
    if (!trimmed) { setError('Введи номер телефона'); return }
    setLoading(true)
    setError(null)
    try {
      const { exists } = await checkPhone(trimmed)
      setStep(exists ? 'login' : 'register-name')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось проверить номер')
    } finally {
      setLoading(false)
    }
  }

  // Обработчик шага «login».
  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    if (!pin.trim()) { setError('Введи PIN'); return }
    setLoading(true)
    setError(null)
    try {
      await login(phone.trim(), pin.trim())
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неверный PIN — попробуй ещё раз')
    } finally {
      setLoading(false)
    }
  }

  // Обработчик шага «register-name».
  function handleRegisterName(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('Введи своё имя'); return }
    setError(null)
    setStep('register-pin')
  }

  // Обработчик шага «register-pin».
  async function handleRegisterPin(e: FormEvent) {
    e.preventDefault()
    if (pin.trim().length < 4) { setError('PIN должен быть минимум 4 символа'); return }
    setLoading(true)
    setError(null)
    try {
      await register(phone.trim(), name.trim(), pin.trim())
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось зарегистрироваться')
    } finally {
      setLoading(false)
    }
  }

  // Выбор обработчика и полей по шагу.
  function renderForm() {
    if (step === 'phone') {
      return (
        <form onSubmit={(e) => void handlePhone(e)} className="flex flex-col gap-4">
          <Field
            label="Номер телефона"
            type="tel"
            value={phone}
            onChange={(v) => { setPhone(v); clearError() }}
            placeholder="+7 700 000 00 00"
            inputMode="tel"
            autoComplete="tel"
            disabled={loading}
          />
          {error && (
            <p className="text-sm font-semibold" style={{ color: 'var(--color-almost-ink)' }}>
              {error}
            </p>
          )}
          <Button3D type="submit" block size="lg" disabled={loading}>
            {loading ? <><Spinner /> Проверяем…</> : 'Продолжить'}
          </Button3D>
        </form>
      )
    }

    if (step === 'login') {
      return (
        <form onSubmit={(e) => void handleLogin(e)} className="flex flex-col gap-4">
          <Field
            label="PIN-код"
            type="password"
            value={pin}
            onChange={(v) => { setPin(v); clearError() }}
            placeholder="••••"
            inputMode="numeric"
            autoComplete="current-password"
            maxLength={12}
            disabled={loading}
          />
          {error && (
            <p className="text-sm font-semibold" style={{ color: 'var(--color-almost-ink)' }}>
              {error}
            </p>
          )}
          <Button3D type="submit" block size="lg" disabled={loading}>
            {loading ? <><Spinner /> Входим…</> : 'Войти'}
          </Button3D>
          <Button3D
            variant="secondary"
            block
            size="md"
            onClick={() => { setStep('phone'); setPin(''); setError(null) }}
            disabled={loading}
          >
            ← Другой номер
          </Button3D>
        </form>
      )
    }

    if (step === 'register-name') {
      return (
        <form onSubmit={handleRegisterName} className="flex flex-col gap-4">
          <Field
            label="Имя"
            value={name}
            onChange={(v) => { setName(v); clearError() }}
            placeholder="Айдана"
            autoComplete="given-name"
            disabled={loading}
          />
          {error && (
            <p className="text-sm font-semibold" style={{ color: 'var(--color-almost-ink)' }}>
              {error}
            </p>
          )}
          <Button3D type="submit" block size="lg" disabled={loading}>
            Далее →
          </Button3D>
          <Button3D
            variant="secondary"
            block
            size="md"
            onClick={() => { setStep('phone'); setError(null) }}
            disabled={loading}
          >
            ← Другой номер
          </Button3D>
        </form>
      )
    }

    // step === 'register-pin'
    return (
      <form onSubmit={(e) => void handleRegisterPin(e)} className="flex flex-col gap-4">
        <Field
          label="Придумай PIN"
          type="password"
          value={pin}
          onChange={(v) => { setPin(v); clearError() }}
          placeholder="минимум 4 символа"
          inputMode="numeric"
          autoComplete="new-password"
          maxLength={12}
          disabled={loading}
        />
        {error && (
          <p className="text-sm font-semibold" style={{ color: 'var(--color-almost-ink)' }}>
            {error}
          </p>
        )}
        <Button3D type="submit" block size="lg" disabled={loading} variant="success">
          {loading ? <><Spinner /> Создаём аккаунт…</> : 'Создать аккаунт'}
        </Button3D>
        <Button3D
          variant="secondary"
          block
          size="md"
          onClick={() => { setStep('register-name'); setPin(''); setError(null) }}
          disabled={loading}
        >
          ← Назад
        </Button3D>
      </form>
    )
  }

  return (
    <div className="relative min-h-dvh bg-bg">
      <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col items-center justify-center px-6 pb-12">
        {/* reveal-анимация всей карточки */}
        <div
          className="reveal flex w-full flex-col items-center gap-6"
          style={{ '--reveal-delay': '0ms' } as CSSProperties}
        >
          {/* Маскот + заголовок */}
          <div className="flex flex-col items-center gap-3 text-center">
            <Mascot mood={mood} size={88} className={mood === 'celebrate' ? 'bob' : ''} />
            <div className="flex flex-col gap-1">
              <h1 className="font-display text-2xl font-extrabold text-ink">
                {stepTitle(step)}
              </h1>
              <p className="text-sm font-semibold text-ink-mute">{stepSub(step, phone)}</p>
            </div>
          </div>

          {/* Форма */}
          <div className="w-full">{renderForm()}</div>
        </div>
      </div>
    </div>
  )
}
