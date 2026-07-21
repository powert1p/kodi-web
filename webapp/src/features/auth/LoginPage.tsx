// Экран входа/регистрации: короткий вход в персональный маршрут.
// Шаги: 1) ввод телефона → проверка /phone/check → ветка login или register.
//        2a) login: PIN → вход.
//        2b) register: имя → класс → PIN → регистрация.

import { useState, type FormEvent } from 'react'
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
  if (step === 'register-grade') return 'В каком классе ты сейчас?'
  return 'Придумай PIN'
}

// Подзаголовок по этапу.
function stepSub(step: Step, phone: string): string {
  if (step === 'phone') return 'Новый ученик сначала настроит цель и пройдёт короткую диагностику'
  if (step === 'login') return `Введи PIN для ${formatPhoneDisplay(phone)} — продолжим ровно с сохранённого шага`
  if (step === 'register-name') return 'Имя появится в твоём учебном маршруте'
  if (step === 'register-grade') return 'Это поможет подобрать честную стартовую сложность — без задач наугад'
  return 'Минимум 4 цифры — по PIN ты вернёшься к сохранённому прогрессу'
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

  // Кнопка «Другой номер» / «Назад» остаётся тихим вторичным действием.
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
          Создать аккаунт и настроить маршрут
        </ApButton>
        <BackButton onClick={() => { setStep('register-grade'); setPin(''); setError(null) }} label="Назад" />
      </form>
    )
  }

  const regIdx = REGISTER_STEPS.indexOf(step)
  return (
    <div className="login-shell">
      <header className="login-header">
        <BrandMark />
        <span>Подготовка к NIS</span>
      </header>
      <main className="login-main">
        <section className="login-form-panel">
          <div aria-live="polite" aria-atomic="true">
            <p className="journey-eyebrow">{step === 'login' ? 'С возвращением' : step === 'phone' ? 'Вход' : 'Регистрация'}</p>
            <h1>{stepTitle(step)}</h1>
            <p className="login-lead">{stepSub(step, phone)}</p>
          </div>

          {regIdx >= 0 && (
            <div className="login-progress" aria-label={`Шаг регистрации ${regIdx + 1} из ${REGISTER_STEPS.length}`}>
              <div>
                <span>Регистрация</span>
                <b>{regIdx + 1} / {REGISTER_STEPS.length}</b>
              </div>
              <ol>
                {REGISTER_STEPS.map((registerStep, index) => (
                  <li key={registerStep} className={index < regIdx ? 'is-done' : index === regIdx ? 'is-current' : ''}>
                    <span className="sr-only">Шаг {index + 1}{index < regIdx ? ' пройден' : index === regIdx ? ' текущий' : ' впереди'}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div key={step} className="login-form-body">{renderForm()}</div>
          <p className="login-privacy">Прогресс хранится в аккаунте. После входа приложение продолжит с последнего подтверждённого шага.</p>
        </section>

        <aside className="login-proof" aria-label="Как начинается подготовка">
          <div className="login-proof__orbit" aria-hidden />
          <p className="journey-eyebrow">Не случайный набор задач</p>
          <h2>Сначала поймём, откуда тебе начинать.</h2>
          <ol>
            <li><span>01</span><div><b>Цель</b><p>Настроим реальный ритм подготовки.</p></div></li>
            <li><span>02</span><div><b>Диагностика</b><p>Найдём сильные навыки и пробелы.</p></div></li>
            <li><span>03</span><div><b>Маршрут</b><p>Начнём с темы, которая даст рост.</p></div></li>
          </ol>
        </aside>
      </main>
    </div>
  )
}
