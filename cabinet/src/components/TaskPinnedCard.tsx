import { useState } from "react";
import type { WrongTask } from "../mock/srez";
import { catalog } from "../mock/srez";
import MathText from "./MathText";

interface Props {
  task: WrongTask;
}

// Закреплённая сверху ошибочная задача — сворачиваемая, чтобы не мешать лесенке.
export default function TaskPinnedCard({ task }: Props) {
  const [open, setOpen] = useState(true);

  return (
    <div className="rounded-[16px] bg-card shadow-[var(--shadow-soft)] ring-1 ring-line">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left focus-visible:outline-none"
      >
        <span className="inline-flex items-center gap-2">
          <span className="rounded-pill bg-brand-wash px-2.5 py-0.5 text-[11px] font-semibold text-brand-deep">
            {catalog[task.primaryMicroSkill] ?? task.topicLabel}
          </span>
          <span className="text-[13px] font-medium text-ink-soft">
            Разбираем задачу
          </span>
        </span>
        <span
          className={`text-muted transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        >
          ▾
        </span>
      </button>

      <div
        className={`grid transition-[grid-template-rows] duration-300 ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <p className="px-4 pb-4 text-[16px] leading-relaxed text-ink">
            <MathText>{task.statement}</MathText>
          </p>
        </div>
      </div>
    </div>
  );
}
