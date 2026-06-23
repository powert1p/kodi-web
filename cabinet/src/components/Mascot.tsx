interface Props {
  size?: number;
  mood?: "calm" | "cheer";
  className?: string;
}

// Округлый большеглазый математик-бадди. Инлайн-SVG, без зависимостей.
// mood="cheer" — поднятые брови + улыбка шире (для закрытия/тьютора).
export default function Mascot({ size = 48, mood = "calm", className }: Props) {
  const cheer = mood === "cheer";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={className}
      role="img"
      aria-label="Математик-помощник"
    >
      {/* тело-капля */}
      <rect
        x="8"
        y="10"
        width="48"
        height="46"
        rx="20"
        fill="var(--color-brand-wash)"
        stroke="var(--color-brand)"
        strokeWidth="2.5"
      />
      {/* «антенна» с плюсиком — математический акцент */}
      <line
        x1="32"
        y1="10"
        x2="32"
        y2="3"
        stroke="var(--color-brand)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="32" cy="3" r="3" fill="var(--color-spark)" />
      {/* глаза */}
      <circle cx="24" cy="30" r="5.5" fill="#fff" stroke="var(--color-ink)" strokeWidth="2" />
      <circle cx="40" cy="30" r="5.5" fill="#fff" stroke="var(--color-ink)" strokeWidth="2" />
      <circle cx="25" cy="31" r="2.4" fill="var(--color-ink)" />
      <circle cx="41" cy="31" r="2.4" fill="var(--color-ink)" />
      {/* щёки */}
      <circle cx="17" cy="38" r="3" fill="var(--color-spark)" opacity="0.35" />
      <circle cx="47" cy="38" r="3" fill="var(--color-spark)" opacity="0.35" />
      {/* рот */}
      {cheer ? (
        <path
          d="M24 42 Q32 50 40 42"
          stroke="var(--color-ink)"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
      ) : (
        <path
          d="M26 43 Q32 47 38 43"
          stroke="var(--color-ink)"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
      )}
    </svg>
  );
}
