import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { LongArrowRightIcon } from '../../icons'

interface SrezFinalProps { wrongCount: number; onContinue: () => void }

export function SrezFinal({ wrongCount, onContinue }: SrezFinalProps) {
  return (
    <section className="tape-card reveal grid w-full overflow-hidden md:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="flex flex-col justify-center px-6 py-10 md:px-10 md:py-14">
        <p className="text-mark text-brand-deep">Срез пройден</p>
        <h1 className="mt-5 text-h1 text-ink">План стал точнее.</h1>
        <p className="mt-5 max-w-xl text-study text-text">{resultLine(wrongCount)}</p>
        <ApButton className="mt-7 w-full sm:w-auto sm:self-start" size="l" onClick={onContinue}>
          К разбору <LongArrowRightIcon size={18} />
        </ApButton>
      </div>
      <Mascot mood="celebrate" size="xl" className="min-h-72 bg-brand-soft/40" />
    </section>
  )
}

function resultLine(n: number): string {
  if (n === 0) return 'Все ответы сошлись. Следующий шаг появится в учебном пути.'
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return `В ${n} задаче нашёлся шаг для разбора.`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `В ${n} задачах нашлись шаги для разбора.`
  return `В ${n} задачах нашлись шаги для разбора.`
}
