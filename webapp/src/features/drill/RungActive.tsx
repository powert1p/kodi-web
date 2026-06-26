import { useState } from 'react'
import type { FormEvent } from 'react'
import { MathText } from '../../components/MathText'
import { Button3D } from '../../components/Button3D'
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

// Активная ступень — единственная тактильная карточка лесенки.
// compute → числовое поле, choose → 3D-кнопки-варианты. Подсказка и reveal
// растут под формой. Лейбл микро-навыка крупный (контраст с тихими ступенями).
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
    <div className="card-flat flex flex-col gap-3 rounded-(--radius-card) p-4 ring-2 ring-primary/15">
      {/* Эйнбров: микро-навык + метка ступени */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[0.6rem] font-extrabold uppercase tracking-[0.14em] text-primary-ink">
          {rung.microSkill}
        </span>
        <span className="font-num text-[0.65rem] font-extrabold tabular-nums text-ink-mute">
          {rung.kind === 'easier' ? 'разминка' : `шаг ${index}`}
        </span>
      </div>

      {/* Инструкция шага */}
      <p className="font-display text-[1.2rem] font-black leading-[1.15] tracking-tight text-ink">
        <MathText text={rung.instruction} />
      </p>

      {/* Ввод: число или варианты */}
      {isChoose ? (
        <div className="grid grid-cols-2 gap-2.5">
          {STEP3_OPTIONS.map((opt) => (
            <Button3D
              key={opt}
              variant="secondary"
              size="lg"
              onClick={() => handleChoose(opt)}
              className="capitalize"
            >
              {opt} цена
            </Button3D>
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
            className="font-num min-w-0 flex-1 rounded-(--radius-field) border-[1.5px] border-border bg-surface-soft px-4 text-base font-extrabold tabular-nums text-ink placeholder:font-bold placeholder:text-ink-mute focus:border-primary focus:bg-surface"
          />
          <Button3D type="submit" variant="primary" size="lg" disabled={!value.trim()}>
            Проверить
          </Button3D>
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
        <details className="rounded-(--radius-field) bg-surface-soft p-3" open>
          <summary className="cursor-pointer text-xs font-extrabold text-revisit-ink">
            Покажу, как делается этот шаг
          </summary>
          <p className="mt-2 text-sm font-bold leading-snug text-ink">
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
