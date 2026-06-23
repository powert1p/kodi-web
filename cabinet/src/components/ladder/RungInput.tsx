import { useMemo, useState } from "react";
import { asciiToTex } from "../../lib/math";

interface Props {
  onSubmit: (value: string) => void;
  disabled?: boolean;
  wobble?: boolean; // тёплое покачивание после неверного ответа
}

// Поле ответа с ЖИВЫМ KaTeX-превью того, что печатает ученик (ASCII 2/3 → дробь).
// Принимает простой ASCII, сравнение — после нормализации (в useLadder).
export default function RungInput({ onSubmit, disabled, wobble }: Props) {
  const [value, setValue] = useState("");
  const preview = useMemo(() => asciiToTex(value), [value]);

  const handle = (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    onSubmit(value);
    setValue("");
  };

  return (
    <form
      onSubmit={handle}
      className={`rounded-[16px] bg-card p-3 shadow-[var(--shadow-soft)] ring-1 ring-line ${
        wobble ? "animate-wobble ring-spark/40" : ""
      }`}
    >
      <div className="flex items-center gap-2">
        <input
          inputMode="text"
          autoComplete="off"
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Например 2/3"
          aria-label="Твой ответ"
          className="min-w-0 flex-1 rounded-[12px] bg-paper px-3.5 py-3 font-num tabular text-[16px] text-ink placeholder:text-muted outline-none ring-1 ring-line transition focus:ring-2 focus:ring-brand disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="shrink-0 rounded-[12px] bg-brand px-5 py-3 text-[15px] font-semibold text-white shadow-[var(--shadow-soft)] transition-[background,transform] hover:bg-brand-deep active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none"
        >
          Проверить
        </button>
      </div>

      {/* живое превью набранного */}
      <div className="mt-2 min-h-[26px] px-1 text-[15px] text-ink-soft">
        {value.trim() ? (
          <span className="inline-flex items-center gap-2 text-[13px] text-muted">
            <span>Ты вводишь:</span>
            <span
              className="text-ink"
              dangerouslySetInnerHTML={{ __html: preview }}
            />
          </span>
        ) : (
          <span className="text-[13px] text-muted/70">
            Пиши дробь как 2/3 или число
          </span>
        )}
      </div>
    </form>
  );
}
