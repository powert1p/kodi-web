import { useEffect, useState } from "react";

interface Props {
  // целевой уровень 0..1, до которого тикает после успеха
  target: number;
}

// Ярлык по порогам — Space Grotesk. Никаких списаний очков.
function tier(v: number): string {
  if (v >= 0.85) return "Освоено";
  if (v >= 0.6) return "Уверенно";
  return "Разбираюсь";
}

// Метр освоения: тикает от прошлого к целевому уровню после закрытия.
export default function MasteryMeter({ target }: Props) {
  const [value, setValue] = useState(Math.max(0, target - 0.34));

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setValue(target);
      return;
    }
    const t = setTimeout(() => setValue(target), 350);
    return () => clearTimeout(t);
  }, [target]);

  return (
    <div className="rounded-[16px] bg-card p-4 shadow-[var(--shadow-soft)] ring-1 ring-line">
      <div className="flex items-baseline justify-between">
        <span className="text-[13px] font-medium text-ink-soft">
          Уровень понимания
        </span>
        <span className="font-num tabular text-[15px] font-bold text-got">
          {tier(value)}
        </span>
      </div>
      <div className="mt-2.5 h-3 overflow-hidden rounded-pill bg-paper ring-1 ring-line">
        <div
          className="h-full rounded-pill bg-got"
          style={{
            width: `${Math.round(value * 100)}%`,
            transition: "width 0.9s var(--ease-spring)",
          }}
        />
      </div>
      <div className="mt-1.5 text-right">
        <span className="font-num tabular text-[12px] text-muted">
          {Math.round(value * 100)}%
        </span>
      </div>
    </div>
  );
}
