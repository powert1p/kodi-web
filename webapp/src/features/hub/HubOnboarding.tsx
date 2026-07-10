import { useNavigate } from 'react-router-dom'
import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'

// Пустой hub для НОВИЧКА (has_activity=false): онбординг, БЕЗ праздника.
// Кёди-протокол §5 «Вход / пустой хаб» — mood hi, тёплое знакомство по имени
// (единственный экран, где Кёди представляется) + единственный primary-CTA на срез.
// tone brand-soft: эта карточка — единственный активный фокус экрана (§4), поэтому
// берёт тёплый бренд-тон (как HubHero), а не нейтральный surface — так новичок
// визуально отличается от ветерана «всё разобрано».
export function HubOnboarding() {
  const navigate = useNavigate()

  return (
    <ApCard
      as="section"
      tone="brand-soft"
      padding="l"
      className="flex flex-col items-center gap-5 text-center"
    >
      <Mascot mood="hi" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h1 className="text-h2 text-ink">Привет! Я Кёди</h1>
        <p className="mx-auto max-w-[17rem] text-study text-text">
          Помогаю разбирать ошибки по математике. Сначала узнаем, с чего начать:
          короткий срез — 12 задач, минут десять.
        </p>
      </div>
      <ApButton variant="primary" size="l" full onClick={() => navigate('/srez')}>
        Начать мини-срез
      </ApButton>
    </ApCard>
  )
}
