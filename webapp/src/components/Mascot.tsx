import learner420 from '../assets/brand/squirrel-learner-420.webp'
import learner840 from '../assets/brand/squirrel-learner-840.webp'
import coach420 from '../assets/brand/squirrel-coach-420.webp'
import coach840 from '../assets/brand/squirrel-coach-840.webp'
import celebrate420 from '../assets/brand/squirrel-celebrate-420.webp'
import celebrate840 from '../assets/brand/squirrel-celebrate-840.webp'
import empathy420 from '../assets/brand/squirrel-empathy-420.webp'
import rest420 from '../assets/brand/squirrel-rest-420.webp'

export type MascotMood = 'hi' | 'thinking' | 'celebrate' | 'oops' | 'rest'
type Size = 's' | 'm' | 'l' | 'xl'

const SIZE: Record<Size, string> = {
  s: 'h-14 w-20',
  m: 'h-24 w-32',
  l: 'h-44 w-56',
  xl: 'h-full w-full',
}

const LABEL: Record<MascotMood, string> = {
  hi: 'Белка Кёди изучает решение в тетради',
  thinking: 'Белка Кёди помогает найти следующий шаг',
  celebrate: 'Белки AiPlus празднуют верное решение',
  oops: 'Белки AiPlus поддерживают после ошибки',
  rest: 'Белки AiPlus отдыхают с книгой',
}

const ASSET = {
  hi: { small: learner420, large: learner840, width: 840, height: 609 },
  thinking: { small: coach420, large: coach840, width: 840, height: 1012 },
  celebrate: { small: celebrate420, large: celebrate840, width: 840, height: 709 },
  oops: { small: empathy420, large: empathy420, width: 420, height: 420 },
  rest: { small: rest420, large: rest420, width: 420, height: 420 },
} satisfies Record<MascotMood, { small: string; large: string; width: number; height: number }>

interface MascotProps {
  mood?: MascotMood
  size?: Size
  className?: string
  decorative?: boolean
  eager?: boolean
}

// Только реальные белки из бренд-папки пользователя. Active Drill/Srez не должны
// рендерить этот компонент: персонаж зарезервирован для входа, empty/error и closure.
export function Mascot({
  mood = 'hi',
  size = 'm',
  className = '',
  decorative = false,
  eager = false,
}: MascotProps) {
  const asset = ASSET[mood]

  return (
    <span
      className={['mascot-frame block shrink-0', SIZE[size], className].join(' ')}
      role={decorative ? undefined : 'img'}
      aria-label={decorative ? undefined : LABEL[mood]}
      aria-hidden={decorative || undefined}
    >
      <img
        src={asset.small}
        srcSet={asset.large === asset.small ? undefined : `${asset.small} 420w, ${asset.large} 840w`}
        sizes={size === 'xl' ? '(min-width: 800px) 36vw, 50vw' : size === 'l' ? '224px' : '128px'}
        alt=""
        width={asset.width}
        height={asset.height}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
      />
    </span>
  )
}
