import { useEffect } from "react";
import confetti from "canvas-confetti";
import Mascot from "./Mascot";

// Пустое состояние: все ошибки разобраны — самый большой праздник.
export default function EmptyAllClear() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    confetti({
      particleCount: 90,
      spread: 75,
      origin: { y: 0.4 },
      colors: ["#2563eb", "#14b8a6", "#f59e0b", "#ff6b57"],
    });
  }, []);

  return (
    <section className="rounded-[20px] bg-card p-8 text-center shadow-[var(--shadow-raised)] ring-1 ring-line">
      <div className="flex justify-center">
        <Mascot size={72} mood="cheer" />
      </div>
      <h2 className="font-display text-[22px] font-bold text-ink mt-4">
        Все ошибки разобраны! 🎉
      </h2>
      <p className="text-[14px] text-ink-soft mt-2 leading-relaxed">
        Ты прошёл весь срез сам. Это и есть рост — приходи за новым.
      </p>
    </section>
  );
}
