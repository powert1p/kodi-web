interface StatusRowProps {
  /** Дни подряд (огонёк-streak). */
  streak: number
  /** Накопленные очки/XP. */
  points: number
}

// Верхняя статус-строка геймификации: огонёк-streak (янтарь) + XP-кристалл (оранжевый).
// Плоские чипы с тонким бордером — глубина приберегается для 3D-кнопок.
// Табличные цифры, чтобы счётчики не «прыгали».
export function StatusRow({ streak, points }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between gap-2">
      {/* Streak */}
      <span className="card-flat inline-flex items-center gap-1.5 rounded-(--radius-pill) px-3 py-1.5">
        <FlameIcon />
        <span className="font-num text-base font-extrabold tabular-nums text-ink">
          {streak}
        </span>
      </span>

      {/* Очки / XP */}
      <span className="card-flat inline-flex items-center gap-1.5 rounded-(--radius-pill) px-3 py-1.5">
        <GemIcon />
        <span className="font-num text-base font-extrabold tabular-nums text-ink">
          {points.toLocaleString('ru-RU')}
        </span>
      </span>
    </div>
  )
}

function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
      <path
        d="M12 2c1 3-1 4.5-2.5 6.5C8 10.5 7 12 7 14a5 5 0 0 0 10 0c0-2.2-1.2-3.8-2.3-5.2C13.4 7 13 4.5 12 2Z"
        fill="var(--color-secondary)"
      />
      <path
        d="M12 11c.7 1.4-.4 2.2-.9 3.2-.4.8-.1 2.3 1.4 2.5 1.6.2 2.5-1 2.5-2.4 0-1.5-1.4-2.3-3-3.3Z"
        fill="#fff"
        opacity="0.85"
      />
    </svg>
  )
}

function GemIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
      <path
        d="M6 3h12l3 5-9 13L3 8l3-5Z"
        fill="var(--color-primary)"
      />
      <path d="M3 8h18M9 3l3 5 3-5M12 8l0 13" fill="none" stroke="#fff" strokeWidth="1.4" opacity="0.6" />
    </svg>
  )
}
