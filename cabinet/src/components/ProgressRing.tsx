interface Props {
  done: number;
  total: number;
  size?: number;
}

// Кольцо прогресса хаба: «разобрано N из total». Цифры — Space Grotesk tabular.
// Заполнение анимируется через transition stroke-dashoffset (transform/opacity-free, ок).
export default function ProgressRing({ done, total, size = 92 }: Props) {
  const stroke = 9;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = total === 0 ? 1 : done / total;
  const offset = c * (1 - pct);

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      aria-label={`Разобрано ${done} из ${total}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.25)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#fff"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.7s var(--ease-spring)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
        <span className="font-num tabular text-[26px] font-bold leading-none">
          {done}
        </span>
        <span className="font-num tabular text-[11px] opacity-80 leading-none mt-0.5">
          из {total}
        </span>
      </div>
    </div>
  );
}
