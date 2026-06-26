// Экран входа / регистрации в стиле AiPlus (плоский, белый фон, бренд-оранжевый).
// Шаги: 1) ввод телефона → проверка /phone/check → ветка login или register.
//        2a) login: PIN → вход.
//        2b) register: имя → PIN → регистрация.
// Маскот приветствует, поддерживающий тон при ошибках (без «злого красного»).

import { useState, type FormEvent, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApTextField } from '../../components/ApTextField'
import { LeftIcon } from '../../icons'
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

  // Кнопка «← Другой номер» / «← Назад» (outlined AiPlus).
  function BackButton({ onClick, label }: { onClick: () => void; label: string }) {
    return (
      <ApButton variant="outlined" size="s" block onClick={onClick} disabled={loading}>
        <LeftIcon size={16} />
        {label}
      </ApButton>
    )
  }

  // Выбор обработчика и полей по шагу.
  function renderForm() {
    if (step === 'phone') {
      return (
        <form onSubmit={(e) => void handlePhone(e)} className="flex flex-col gap-4">
          <ApTextField
            label="Номер телефона"
            type="tel"
            value={phone}
            onChange={(e) => { setPhone(e.target.value); clearError() }}
            placeholder="+7 700 000 00 00"
            inputMode="tel"
            autoComplete="tel"
            fieldSize="lg"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" block size="m" isLoading={loading}>
            Продолжить
          </ApButton>
        </form>
      )
    }

    if (step === 'login') {
      return (
        <form onSubmit={(e) => void handleLogin(e)} className="flex flex-col gap-4">
          <ApTextField
            label="PIN-код"
            type="password"
            value={pin}
            onChange={(e) => { setPin(e.target.value); clearError() }}
            placeholder="••••"
            inputMode="numeric"
            autoComplete="current-password"
            maxLength={12}
            fieldSize="lg"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" block size="m" isLoading={loading}>
            Войти
          </ApButton>
          <BackButton onClick={() => { setStep('phone'); setPin(''); setError(null) }} label="Другой номер" />
        </form>
      )
    }

    if (step === 'register-name') {
      return (
        <form onSubmit={handleRegisterName} className="flex flex-col gap-4">
          <ApTextField
            label="Имя"
            value={name}
            onChange={(e) => { setName(e.target.value); clearError() }}
            placeholder="Айдана"
            autoComplete="given-name"
            fieldSize="lg"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" block size="m">
            Далее
          </ApButton>
          <BackButton onClick={() => { setStep('phone'); setError(null) }} label="Другой номер" />
        </form>
      )
    }

    // step === 'register-pin'
    return (
      <form onSubmit={(e) => void handleRegisterPin(e)} className="flex flex-col gap-4">
        <ApTextField
          label="Придумай PIN"
          type="password"
          value={pin}
          onChange={(e) => { setPin(e.target.value); clearError() }}
          placeholder="минимум 4 символа"
          inputMode="numeric"
          autoComplete="new-password"
          maxLength={12}
          fieldSize="lg"
          disabled={loading}
          error={error}
        />
        <ApButton type="submit" block size="m" isLoading={loading}>
          Создать аккаунт
        </ApButton>
        <BackButton onClick={() => { setStep('register-name'); setPin(''); setError(null) }} label="Назад" />
      </form>
    )
  }

  return (
    <div className="relative min-h-dvh bg-bg-primary">
      <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col items-center justify-center px-6 pb-12">
        <div
          className="reveal flex w-full flex-col items-center gap-6"
          style={{ '--reveal-delay': '0ms' } as CSSProperties}
        >
          {/* Маскот + заголовок */}
          <div className="flex flex-col items-center gap-3 text-center">
            <Mascot mood={mood} size={88} className={mood === 'celebrate' ? 'bob' : ''} />
            <div className="flex flex-col gap-1">
              <h1 className="text-h2 text-text-primary">{stepTitle(step)}</h1>
              <p className="text-caption1 text-text-secondary">{stepSub(step, phone)}</p>
            </div>
          </div>

          {/* Форма */}
          <div className="w-full">{renderForm()}</div>
        </div>
      </div>
    </div>
  )
}
