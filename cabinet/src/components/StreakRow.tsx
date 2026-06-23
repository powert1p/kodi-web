import { learner } from "../mock/srez";

// Тихая строка мотивации: дни разбора (не точность!) + пожизненный счётчик освоенного.
export default function StreakRow() {
  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center gap-1.5 rounded-pill bg-spark-wash px-3 py-1.5 text-[13px] font-medium text-spark ring-1 ring-spark/20">
        <span aria-hidden>🔥</span>
        <span className="font-num tabular font-semibold">{learner.streakDays}</span>
        дня разбираешь ошибки
      </span>
      <span className="inline-flex items-center gap-1.5 rounded-pill bg-card px-3 py-1.5 text-[13px] text-ink-soft ring-1 ring-line">
        освоено
        <span className="font-num tabular font-semibold text-ink">
          {learner.lifetimeMastered}
        </span>
      </span>
    </div>
  );
}
