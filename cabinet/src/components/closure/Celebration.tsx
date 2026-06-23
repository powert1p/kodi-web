import { useEffect } from "react";
import confetti from "canvas-confetti";
import { motion } from "framer-motion";
import Mascot from "../Mascot";
import MasteryMeter from "../MasteryMeter";

interface Props {
  biggest: boolean; // последняя ошибка среза — самый большой праздник
  onContinue: () => void;
  remaining: number;
}

// Праздник закрытия: конфетти + бадди + метр освоения. Хвалим усилие, не способность.
export default function Celebration({ biggest, onContinue, remaining }: Props) {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const burst = (y: number, count: number) =>
      confetti({
        particleCount: count,
        spread: biggest ? 90 : 65,
        origin: { y },
        colors: ["#2563eb", "#14b8a6", "#f59e0b", "#ff6b57"],
      });
    burst(0.45, biggest ? 120 : 70);
    if (biggest) setTimeout(() => burst(0.5, 80), 250);
  }, [biggest]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ease: [0.34, 1.56, 0.64, 1], duration: 0.5 }}
      className="space-y-4 text-center"
    >
      <motion.div
        className="flex justify-center"
        animate={{ rotate: [0, -6, 6, 0] }}
        transition={{ duration: 0.6, ease: "easeInOut" }}
      >
        <Mascot size={84} mood="cheer" />
      </motion.div>

      <div>
        <h2 className="font-display text-[28px] font-bold text-ink leading-tight">
          {biggest ? "Весь срез разобран!" : "Ты разобрался сам!"}
        </h2>
        <p className="mt-2 text-[15px] leading-relaxed text-ink-soft">
          {biggest
            ? "Ты прошёл каждую ошибку до конца. Так и растёт мозг 🌱"
            : "Сам нашёл путь к ответу — это и есть понимание."}
        </p>
      </div>

      <MasteryMeter target={biggest ? 0.92 : 0.78} />

      <button
        type="button"
        onClick={onContinue}
        className="w-full rounded-[16px] bg-brand px-5 py-3.5 text-[15px] font-semibold text-white shadow-[var(--shadow-raised)] transition hover:bg-brand-deep active:scale-[0.98] focus-visible:outline-none"
      >
        {remaining > 0
          ? `К срезу · осталось ${remaining}`
          : "Вернуться к срезу"}
      </button>
    </motion.section>
  );
}
