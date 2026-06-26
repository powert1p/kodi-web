import { useState } from 'react'
import type { FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { ApButton } from '../../components/ApButton'
import { HintBanner } from './HintBanner'
import type { Rung } from '../../lib/ladder'
import { STEP3_OPTIONS } from './mock'

interface RungActiveProps {
  rung: Rung
  /** Номер ступени для метки (1-based, по оригинальным шагам). */
  index: number
  /** Показать подсказку (ladder.hint). */
  hint: boolean
  /** Показать «было сложно» reveal как последнюю опору. */
  showReveal: boolean
  /** Климб-даун только что вставил эту ступень (другой тон баннера). */
  justInserted: boolean
  /** Сабмит ответа — драйвит ladder.submit. */
  onSubmit: (value: string) => void
}

// Активная ступень — единственная выделенная карточка лесенки (AiPlus selected-card:
// фон bg-light-brand-warning + бордер stroke-brand, радиус 14). compute → поле ввода,
// choose → outlined-кнопки-варианты. Подсказка/reveal растут под формой.
export function RungActive({
  rung,
  index,
  hint,
  showReveal,
  justInserted,
  onSubmit,
}: RungActiveProps) {
  const [value, setValue] = useState('')
  const isChoose = rung.kind === 'original' && rung.expected_value === 'новая'

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!value.trim()) return
    onSubmit(value)
    setValue('')
  }

  const handleChoose = (opt: string) => {
    onSubmit(opt)
    setValue('')
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-stroke-brand bg-bg-light-brand-warning p-4">
      {/* Эйбров: микро-навык + метка ступени */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-caption2-medium uppercase tracking-[0.1em] text-text-brand">
          {rung.microSkill}
        </span>
        <span className="font-num text-caption2 tabular-nums text-text-secondary">
          {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
        </span>
      </div>

      {/* Инструкция шага */}
      <p className="text-h3 text-text-primary">
        <MathText text={rung.instruction} />
      </p>

      {/* Ввод: число или варианты */}
      {isChoose ? (
        <div className="grid grid-cols-2 gap-2.5">
          {STEP3_OPTIONS.map((opt) => (
            <ApButton
              key={opt}
              variant="outlined"
              size="m"
              onClick={() => handleChoose(opt)}
              className="capitalize"
            >
              {opt} цена
            </ApButton>
          ))}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex items-stretch gap-2.5">
          <input
            inputMode="decimal"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Твой ответ"
            aria-label="Введите ответ"
            autoComplete="off"
            className="font-num min-w-0 flex-1 rounded-lg border border-stroke-primary-disabled bg-bg-primary px-4 text-body tabular-nums text-text-primary placeholder:text-text-secondary outline-none focus:border-[1.5px] focus:border-stroke-brand"
            style={{ fontSize: '16px' }}
          />
          <ApButton type="submit" variant="filled" size="m" disabled={!value.trim()}>
            Проверить
          </ApButton>
        </form>
      )}

      {/* Подсказка (наводящий вопрос, не ответ) */}
      {hint && rung.kind === 'easier' && justInserted && (
        <HintBanner text="Маленький разогрев перед основным шагом — у тебя получится!" variant="easier" />
      )}
      {hint && !(rung.kind === 'easier' && justInserted) && (
        <HintBanner text={socraticHint(rung)} variant="hint" />
      )}

      {/* Reveal — разобранный шаг как последняя опора (НЕ финальный ответ задачи) */}
      {showReveal && rung.reveal && (
        <details className="rounded-lg bg-bg-primary p-3" open>
          <summary className="cursor-pointer text-caption1-medium text-text-info">
            Покажу, как делается этот шаг
          </summary>
          <p className="mt-2 text-caption1 text-text-primary">
            <MathText text={rung.reveal} />
          </p>
        </details>
      )}
    </div>
  )
}

// Сократическая подсказка по микро-навыку: наводит, но НЕ даёт ответ.
function socraticHint(rung: Rung): string {
  const bySkill: Record<string, string> = {
    'Процент от числа': 'Чтобы найти процент от числа — умножь число на долю. А $15\\%$ это сколько в виде дроби?',
    'Прибавить процент': 'Рост означает прибавку. К исходной цене прибавь то, что насчитал на прошлом шаге.',
    'База процента': 'Подумай: после подорожания товар уже стоит дороже. От какой суммы логично считать скидку?',
    'Вычесть процент': 'Снижение — это вычитание. Сначала найди $10\\%$ от текущей цены, потом отними.',
  }
  return bySkill[rung.microSkill] ?? 'Загляни на прошлый шаг — ответ оттуда подскажет, что делать здесь.'
}
