import ProgressRing from "./ProgressRing";
import { srez } from "../mock/srez";

interface Props {
  done: number;
  total: number;
}

// Шапка-градиент хаба. Прогресс смотрит вперёд, а не считает провалы.
export default function HubHeader({ done, total }: Props) {
  return (
    <header
      className="rounded-[20px] p-5 text-white shadow-[var(--shadow-raised)] relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, var(--color-brand-deep), var(--color-brand-indigo))",
      }}
    >
      {/* мягкий блик */}
      <div className="absolute -right-8 -top-10 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
      <div className="relative flex items-start gap-4">
        <ProgressRing done={done} total={total} />
        <div className="min-w-0 flex-1">
          <p className="font-num tabular text-[12px] uppercase tracking-wider text-white/70">
            Срез · {srez.date}
          </p>
          <h1 className="font-display text-[24px] font-bold leading-tight mt-0.5">
            {srez.title}
          </h1>
          <p className="text-[14px] leading-snug text-white/85 mt-1.5">
            Разберём вместе — здесь растёт мозг 🌱
          </p>
        </div>
      </div>

      <div className="relative mt-4 flex items-center gap-2 rounded-[12px] bg-white/12 px-3 py-2">
        <span className="font-num tabular text-[14px] font-semibold">
          Разобрано {done} из {total}
        </span>
        <span className="text-[13px] text-white/75">
          · осталось {total - done}
        </span>
      </div>
    </header>
  );
}
