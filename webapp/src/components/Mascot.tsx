// Маскот «Кёди» — ОРИГИНАЛЬНЫЙ дружелюбный росток-семечко в бренд-оранжевом.
// Не сова и не чужой персонаж: круглое тельце-капля + два листочка-«ушка»,
// ободряющая мимика. Растёт вместе с настроением (mood). Чистый inline SVG.

type Mood = 'cheer' | 'think' | 'celebrate' | 'oops'

interface MascotProps {
  mood?: Mood
  /** Размер стороны в px (квадрат). */
  size?: number
  className?: string
}

// Глаза по настроению: радостные дуги, сосредоточенные точки, зажмур на празднике.
function Eyes({ mood }: { mood: Mood }) {
  const eyeColor = 'var(--color-ink)'
  if (mood === 'celebrate') {
    // зажмуренные «^ ^» от счастья
    return (
      <g
        fill="none"
        stroke={eyeColor}
        strokeWidth="3.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M40 55 l6 -6 l6 6" />
        <path d="M68 55 l6 -6 l6 6" />
      </g>
    )
  }
  if (mood === 'think') {
    // сосредоточенные точки + приподнятая бровь
    return (
      <g fill={eyeColor}>
        <circle cx="46" cy="54" r="4" />
        <circle cx="74" cy="54" r="4" />
        <path
          d="M68 45 q6 -4 12 -1"
          fill="none"
          stroke={eyeColor}
          strokeWidth="3"
          strokeLinecap="round"
        />
      </g>
    )
  }
  if (mood === 'oops') {
    // мягкие большие глаза-капли (виновато, но без стыда)
    return (
      <g fill={eyeColor}>
        <circle cx="46" cy="55" r="5" />
        <circle cx="74" cy="55" r="5" />
      </g>
    )
  }
  // cheer — обычные тёплые круглые глаза с бликом
  return (
    <g>
      <circle cx="46" cy="54" r="5" fill={eyeColor} />
      <circle cx="74" cy="54" r="5" fill={eyeColor} />
      <circle cx="48" cy="52" r="1.6" fill="#fff" />
      <circle cx="76" cy="52" r="1.6" fill="#fff" />
    </g>
  )
}

// Рот по настроению.
function Mouth({ mood }: { mood: Mood }) {
  const stroke = 'var(--color-primary-edge)'
  if (mood === 'celebrate') {
    return <path d="M50 66 q10 12 20 0" fill="#fff" stroke={stroke} strokeWidth="3" />
  }
  if (mood === 'think') {
    return (
      <path d="M52 68 h16" fill="none" stroke={stroke} strokeWidth="3.4" strokeLinecap="round" />
    )
  }
  if (mood === 'oops') {
    return (
      <path
        d="M52 70 q8 -6 16 0"
        fill="none"
        stroke={stroke}
        strokeWidth="3.4"
        strokeLinecap="round"
      />
    )
  }
  return (
    <path
      d="M50 65 q10 9 20 0"
      fill="none"
      stroke={stroke}
      strokeWidth="3.6"
      strokeLinecap="round"
    />
  )
}

const LABEL: Record<Mood, string> = {
  cheer: 'Кёди улыбается',
  think: 'Кёди думает',
  celebrate: 'Кёди празднует',
  oops: 'Кёди подбадривает',
}

export function Mascot({ mood = 'cheer', size = 64, className = '' }: MascotProps) {
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label={LABEL[mood]}
    >
      {/* два листочка-«ушка» сверху (росток) */}
      <path
        d="M60 30 C 50 8, 28 8, 30 30 C 44 32, 56 30, 60 30 Z"
        fill="var(--color-success)"
      />
      <path
        d="M60 30 C 70 8, 92 8, 90 30 C 76 32, 64 30, 60 30 Z"
        fill="var(--color-success-edge)"
      />
      {/* стебелёк */}
      <rect x="57" y="26" width="6" height="14" rx="3" fill="var(--color-success-edge)" />

      {/* тельце-капля в бренд-оранжевом */}
      <path
        d="M60 36
           C 90 36, 102 60, 102 78
           C 102 100, 84 112, 60 112
           C 36 112, 18 100, 18 78
           C 18 60, 30 36, 60 36 Z"
        fill="var(--color-primary)"
      />
      {/* мягкий верхний блик (объём без тяжёлых теней) */}
      <ellipse cx="46" cy="50" rx="22" ry="14" fill="#fff" opacity="0.16" />

      {/* щёчки */}
      <circle cx="34" cy="68" r="6" fill="var(--color-primary-edge)" opacity="0.45" />
      <circle cx="86" cy="68" r="6" fill="var(--color-primary-edge)" opacity="0.45" />

      <Eyes mood={mood} />
      <Mouth mood={mood} />
    </svg>
  )
}
