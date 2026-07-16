// Экран входа/регистрации v11: короткая форма в системе «Лента решения».
// Шаги: 1) ввод телефона → проверка /phone/check → ветка login или register.
//        2a) login: PIN → вход.
//        2b) register: имя → класс → PIN → регистрация.
// Маскот приветствует, поддерживающий тон при ошибках (без «злого красного»).

import { useState, type FormEvent } from 'react'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApTextField } from '../../components/ApTextField'
import { BrandMark } from '../../components/BrandMark'
import { GradeSelect } from './GradeSelect'
import { LeftIcon } from '../../icons'
import { useAuth } from './AuthContext'
import { checkPhone } from '../../lib/auth'

// Этап формы.
type Step = 'phone' | 'login' | 'register-name' | 'register-grade' | 'register-pin'

// Шаги регистрации как отметки маршрута (тот же язык, что hub/drill/srez).
const REGISTER_STEPS: Step[] = ['register-name', 'register-grade', 'register-pin']

// Заголовок по этапу.
function stepTitle(step: Step): string {
  if (step === 'phone') return 'Привет! Введи номер'
  if (step === 'login') return 'Добро пожаловать!'
  if (step === 'register-name') return 'Как тебя зовут?'
  if (step === 'register-grade') return 'В какой класс идёшь?'
  return 'Придумай PIN'
}

// Подзаголовок по этапу.
function stepSub(step: Step, phone: string): string {
  if (step === 'phone') return 'Введи номер — и откроем твой текущий урок'
  if (step === 'login') return `Введи PIN для ${formatPhoneDisplay(phone)} и продолжай с нужного шага`
  if (step === 'register-name') return 'Имя поможет сохранять твой учебный путь'
  if (step === 'register-grade') return 'Подберём объяснение и сложность по классу'
  return 'Минимум 4 цифры — по нему ты вернёшься к уроку'
}

// Консистентный формат телефона для ОТОБРАЖЕНИЯ (+7 700 000 00 00) — вне
// зависимости от того, как ученик набрал номер (пробелы/без пробелов/8 вместо 7).
// Значение, которое реально уходит на сервер, не трогаем (auth.ts принимает
// сырой ввод как есть). Нестандартный ввод (не 11 цифр) — показываем как есть,
// не гадаем и не ломаем номер.
function formatPhoneDisplay(raw: string): string {
  const digits = raw.replace(/\D/g, '').replace(/^8(\d{10})$/, '7$1')
  if (digits.length !== 11 || digits[0] !== '7') return raw.trim()
  const d = digits.slice(1)
  return `+7 ${d.slice(0, 3)} ${d.slice(3, 6)} ${d.slice(6, 8)} ${d.slice(8, 10)}`
}

// Браузер сообщает о потере сети техническим `Failed to fetch`. Ребёнку
// показываем понятное действие, а содержательные ответы backend сохраняем.
function userFacingAuthError(error: unknown, fallback: string): string {
  if (error instanceof TypeError || (error instanceof Error && error.message === 'Failed to fetch')) {
    return 'Не получилось подключиться. Проверь интернет и попробуй ещё раз.'
  }
  return error instanceof Error ? error.message : fallback
}

export function LoginPage() {
  const { login, register } = useAuth()

  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [name, setName] = useState('')
  const [grade, setGrade] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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
      setError(userFacingAuthError(err, 'Не удалось проверить номер'))
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
    } catch (err) {
      setError(userFacingAuthError(err, 'Неверный PIN — попробуй ещё раз'))
    } finally {
      setLoading(false)
    }
  }

  // Обработчик шага «register-name».
  function handleRegisterName(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('Введи своё имя'); return }
    setError(null)
    setStep('register-grade')
  }

  // Обработчик шага «register-grade» (класс обязателен — кнопка заблокирована без выбора).
  function handleRegisterGrade(e: FormEvent) {
    e.preventDefault()
    if (grade === null) { setError('Выбери класс'); return }
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
      await register(phone.trim(), name.trim(), pin.trim(), grade)
    } catch (err) {
      setError(userFacingAuthError(err, 'Не удалось зарегистрироваться'))
    } finally {
      setLoading(false)
    }
  }

  // Кнопка «← Другой номер» / «← Назад» — тихая ghost (ambient-навигация).
  function BackButton({ onClick, label }: { onClick: () => void; label: string }) {
    return (
      <ApButton variant="ghost" size="m" full onClick={onClick} disabled={loading}>
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
            autoFocus
            type="tel"
            value={phone}
            onChange={(e) => { setPhone(e.target.value); clearError() }}
            placeholder="+7 700 000 00 00"
            inputMode="tel"
            autoComplete="tel"
            fieldSize="l"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" full size="m" loading={loading}>
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
            autoFocus
            type="password"
            value={pin}
            onChange={(e) => { setPin(e.target.value); clearError() }}
            placeholder="••••"
            inputMode="numeric"
            autoComplete="current-password"
            maxLength={12}
            fieldSize="l"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" full size="m" loading={loading}>
            Войти и продолжить урок
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
            autoFocus
            value={name}
            onChange={(e) => { setName(e.target.value); clearError() }}
            placeholder="Айдана"
            autoComplete="given-name"
            fieldSize="l"
            disabled={loading}
            error={error}
          />
          <ApButton type="submit" full size="m">
            Далее
          </ApButton>
          <BackButton onClick={() => { setStep('phone'); setError(null) }} label="Другой номер" />
        </form>
      )
    }

    if (step === 'register-grade') {
      return (
        <form onSubmit={handleRegisterGrade} className="flex flex-col gap-4">
          <GradeSelect autoFocus value={grade} onChange={(g) => { setGrade(g); clearError() }} disabled={loading} />
          <ApButton type="submit" full size="m" disabled={grade === null}>
            Далее
          </ApButton>
          <BackButton onClick={() => { setStep('register-name'); setError(null) }} label="Назад" />
        </form>
      )
    }

    // step === 'register-pin'
    return (
      <form onSubmit={(e) => void handleRegisterPin(e)} className="flex flex-col gap-4">
        <ApTextField
          label="Придумай PIN"
          autoFocus
          type="password"
          value={pin}
          onChange={(e) => { setPin(e.target.value); clearError() }}
          placeholder="минимум 4 символа"
          inputMode="numeric"
          autoComplete="new-password"
          maxLength={12}
          fieldSize="l"
          disabled={loading}
          error={error}
        />
        <ApButton type="submit" full size="m" loading={loading}>
          Создать аккаунт и начать
        </ApButton>
        <BackButton onClick={() => { setStep('register-grade'); setPin(''); setError(null) }} label="Назад" />
      </form>
    )
  }

  const regIdx = REGISTER_STEPS.indexOf(step)
  return (
    <div className="studio-grain min-h-dvh bg-paper">
      <header className="mx-auto flex min-h-18 max-w-6xl items-center px-5 md:px-8">
        <BrandMark />
      </header>
      <main className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-6xl items-center gap-6 px-5 py-6 md:px-8 lg:grid-cols-[minmax(22rem,0.82fr)_minmax(22rem,1fr)] lg:gap-12 lg:py-10">
        <section className="tape-card reveal order-1 w-full px-6 py-7 md:px-9 md:py-9">
          <div aria-live="polite" aria-atomic="true">
            <p className="text-mark text-brand-deep">{step === 'login' ? 'С возвращением' : step === 'phone' ? 'Вход' : 'Регистрация'}</p>
            <h1 className="mt-3 text-h2 text-ink">{stepTitle(step)}</h1>
            <p className="mt-3 text-body text-muted">{stepSub(step, phone)}</p>
          </div>

          {regIdx >= 0 && (
            <div className="mt-6" aria-label={`Шаг регистрации ${regIdx + 1} из ${REGISTER_STEPS.length}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-caption1-medium text-ink">Твой маршрут входа</span>
                <span className="font-display rounded-chip bg-brand-soft px-3 py-1 text-caption1-medium text-brand-ink">{regIdx + 1} / {REGISTER_STEPS.length}</span>
              </div>
              <ol className="mt-4 grid grid-cols-3 gap-2">
                {REGISTER_STEPS.map((registerStep, index) => (
                  <li key={registerStep} className={['h-2 rounded-full', index < regIdx ? 'bg-success' : index === regIdx ? 'bg-brand ring-2 ring-brand-soft' : 'bg-ink/15'].join(' ')}>
                    <span className="sr-only">Шаг {index + 1}{index < regIdx ? ' пройден' : index === regIdx ? ' текущий' : ' впереди'}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div key={step} className="mt-6 w-full">{renderForm()}</div>
          <p className="mt-6 rounded-control bg-sage-soft px-4 py-3 text-caption1 text-text">Сначала разберём пример, потом ты решишь сам — шаг за шагом.</p>
        </section>

        <aside className="order-2 grid min-h-60 grid-cols-[minmax(0,1fr)_8rem] items-center overflow-hidden rounded-card border border-ink/10 bg-sage-soft/70 px-5 pt-5 shadow-lift-sm lg:min-h-[34rem] lg:grid-cols-1 lg:grid-rows-[auto_minmax(0,1fr)] lg:px-8 lg:pt-8">
          <div className="self-start">
            <p className="text-mark text-sage-deep">Учёба начинается сразу</p>
            <h2 className="mt-3 max-w-md text-[clamp(27px,4vw,48px)] font-bold leading-[1.02] tracking-[-0.055em] text-ink">Один понятный урок. От примера до самостоятельного решения.</h2>
            <p className="mt-4 hidden max-w-lg text-body text-muted sm:block">После входа откроется текущая тема: разберёшь метод, потренируешься с опорой и применишь его сам.</p>
          </div>
          <Mascot mood="hi" size="xl" eager decorative className="mascot-shadow h-36 self-end lg:h-full lg:max-h-72" />
        </aside>
      </main>
    </div>
  )
}
