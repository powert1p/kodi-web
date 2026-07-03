import { Mascot } from '../../components/Mascot'
import { ApCard } from '../../components/ApCard'
import { ApButton } from '../../components/ApButton'
import { LongArrowRightIcon } from '../../icons'

interface SrezFinalProps {
  wrongCount: number
  onContinue: () => void
}

// Финал среза: празднование прохождения (это не оценка!) + сколько тем нашли
// для прокачки → «К разбору» уводит на хаб с уже инвалидированным списком ошибок.
export function SrezFinal({ wrongCount, onContinue }: SrezFinalProps) {
  return (
    <ApCard padding="l" className="reveal flex flex-col items-center gap-5 py-12 text-center">
      <Mascot mood="celebrate" size="l" className="bob" />
      <div className="flex flex-col gap-2">
        <h2 className="text-h2 text-ink">Срез пройден</h2>
        <p className="max-w-[17rem] text-study text-text">
          Нашли {wrongCount} {topicWord(wrongCount)} для прокачки
        </p>
      </div>
      <ApButton variant="primary" size="m" full onClick={onContinue}>
        К разбору
        <LongArrowRightIcon size={18} />
      </ApButton>
    </ApCard>
  )
}

// Русское склонение «тема/темы/тем» по числу — без него счётчик режет слух.
function topicWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'тему'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'темы'
  return 'тем'
}
