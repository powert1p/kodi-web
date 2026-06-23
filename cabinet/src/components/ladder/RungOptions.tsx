import { useState } from "react";
import type { StepOption } from "../../mock/srez";
import MathText from "../MathText";

interface Props {
  options: StepOption[];
  onSelect: (id: string) => void;
  wobble?: boolean; // тёплое покачивание после неверного выбора
}

// Ступень-выбор: ребёнок РЕШАЕТ, какой подход верный, а не считает.
// Одиночный выбор, кнопки ≥44px, фокусируются с клавиатуры.
export default function RungOptions({ options, onSelect, wobble }: Props) {
  // последний выбранный id — для мягкой подсветки промаха (без красного)
  const [picked, setPicked] = useState<string | null>(null);

  const handle = (id: string) => {
    setPicked(id);
    onSelect(id);
  };

  return (
    <div
      className={`rounded-[16px] bg-card p-3 shadow-[var(--shadow-soft)] ring-1 ring-line ${
        wobble ? "animate-wobble ring-spark/40" : ""
      }`}
      role="group"
      aria-label="Выбери верный вариант"
    >
      <p className="px-1 pb-2 text-[12px] font-medium text-muted">
        Выбери, как рассуждать
      </p>
      <div className="space-y-2">
        {options.map((opt) => {
          const isMiss = wobble && picked === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => handle(opt.id)}
              aria-label={opt.label}
              className={`flex min-h-[52px] w-full items-center gap-3 rounded-[12px] px-4 py-3 text-left text-[15px] text-ink ring-1 transition-[background,box-shadow,transform] active:scale-[0.99] focus-visible:outline-none ${
                isMiss
                  ? "bg-spark-wash ring-spark/40"
                  : "bg-paper ring-line hover:bg-brand-wash hover:ring-brand/25"
              }`}
            >
              <span
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-card text-[12px] font-semibold text-ink-soft ring-1 ring-line"
                aria-hidden
              >
                {opt.id === picked && wobble ? "·" : "?"}
              </span>
              <span className="leading-snug">
                <MathText>{opt.label}</MathText>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
