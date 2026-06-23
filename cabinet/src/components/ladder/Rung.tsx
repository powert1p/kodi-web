import { motion } from "framer-motion";
import type { Rung as RungData } from "../../hooks/useLadder";
import MathText from "../MathText";

interface Props {
  rung: RungData;
  index: number;
  isLast: boolean;
  justInserted: boolean;
}

// Одна ступень лесенки. Решённая — бирюза + пружина; активная — светится,
// под ней тетрадная сетка-память; locked — приглушена; easier — янтарная.
export default function Rung({ rung, index, isLast, justInserted }: Props) {
  const solved = rung.status === "solved";
  const active = rung.status === "active";
  const locked = rung.status === "locked";
  const easier = rung.kind === "easier";

  // Цвета по статусу/типу
  const railColor = solved
    ? "bg-got"
    : active
      ? easier
        ? "bg-almost"
        : "bg-brand"
      : "bg-line";

  return (
    <motion.li
      layout
      initial={
        justInserted
          ? { opacity: 0, height: 0, scale: 0.9 }
          : { opacity: 0, y: 6 }
      }
      animate={{ opacity: 1, height: "auto", y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
      className="relative flex gap-3"
    >
      {/* левый «рельс» с узлом */}
      <div className="flex flex-col items-center">
        <motion.div
          // пружина при решении
          animate={solved ? { scale: [1, 1.25, 1] } : {}}
          transition={{ duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }}
          className={`grid h-9 w-9 place-items-center rounded-full text-[14px] font-bold text-white shadow-[var(--shadow-soft)] ${
            solved
              ? "bg-got"
              : active
                ? easier
                  ? "bg-almost"
                  : "bg-brand"
                : "bg-revisit/50"
          } ${active ? "ring-4 ring-brand/15" : ""}`}
        >
          {solved ? (
            <span aria-hidden>✓</span>
          ) : easier ? (
            <span aria-hidden>↓</span>
          ) : (
            <span className="font-num tabular">{index + 1}</span>
          )}
        </motion.div>
        {!isLast && <div className={`w-1 flex-1 rounded-full ${railColor} opacity-70`} />}
      </div>

      {/* карточка ступени */}
      <div
        className={`mb-3 flex-1 rounded-[16px] p-4 transition-shadow ${
          active
            ? "graph-paper bg-card shadow-[var(--shadow-raised)] ring-1 ring-brand/25"
            : solved
              ? "bg-got-wash ring-1 ring-got/25"
              : easier
                ? "bg-almost-wash ring-1 ring-almost/30"
                : "bg-card/60 ring-1 ring-line"
        } ${locked ? "opacity-55" : ""}`}
      >
        {easier && (
          <p className="mb-1.5 text-[12px] font-semibold text-almost">
            Окей, зайдём проще
          </p>
        )}
        <p
          className={`text-[15px] leading-relaxed ${
            locked ? "text-muted" : "text-ink"
          }`}
        >
          <MathText>{rung.instruction}</MathText>
        </p>
        {solved && (
          <p className="mt-2 text-[12px] font-medium text-got">
            ✓ Готово — поднимаемся выше
          </p>
        )}
      </div>
    </motion.li>
  );
}
