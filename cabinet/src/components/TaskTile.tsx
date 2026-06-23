import { useNavigate } from "react-router-dom";
import { useState } from "react";
import type { WrongTask } from "../mock/srez";
import { catalog } from "../mock/srez";
import { semaphore } from "../lib/semaphore";
import { answerToTex } from "../lib/math";
import MathText from "./MathText";

interface Props {
  task: WrongTask;
  closed: boolean;
}

// Плитка ошибочной задачи. Исходный неверный ответ СКРЫТ по умолчанию —
// раскрывается осознанным тапом, без пристыжения.
export default function TaskTile({ task, closed }: Props) {
  const navigate = useNavigate();
  const [revealed, setRevealed] = useState(false);
  const sem = closed ? semaphore.got : semaphore[task.state];

  return (
    <article
      className={`rounded-[16px] ${sem.wash} p-4 shadow-[var(--shadow-soft)] ring-1 ${sem.ring} transition-shadow hover:shadow-[var(--shadow-raised)]`}
    >
      <button
        type="button"
        onClick={() => navigate(`/task/${task.id}`)}
        className="w-full text-left group rounded-[12px] focus-visible:outline-none"
      >
        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${sem.dot}`} aria-hidden />
            <span className={`text-[12px] font-semibold ${sem.text}`}>
              {closed ? "Разобрано" : sem.label}
            </span>
          </span>
          <span className="rounded-pill bg-card/70 px-2.5 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-line">
            {catalog[task.primaryMicroSkill] ?? task.topicLabel}
          </span>
        </div>

        <p className="mt-2.5 text-[15px] leading-relaxed text-ink group-hover:text-brand-deep transition-colors">
          <MathText>{task.statement}</MathText>
        </p>
      </button>

      <div className="mt-3 flex items-center justify-between">
        {revealed ? (
          <span className="text-[12px] text-muted">
            Прошлый ответ:{" "}
            <span className="font-num tabular text-ink-soft">
              <MathText>{answerToTex(task.wrongAnswer)}</MathText>
            </span>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="text-[12px] text-muted underline decoration-dotted underline-offset-2 hover:text-ink-soft focus-visible:outline-none"
          >
            Показать прошлый ответ
          </button>
        )}

        <button
          type="button"
          onClick={() => navigate(`/task/${task.id}`)}
          className="inline-flex items-center gap-1 rounded-pill bg-brand px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-[var(--shadow-soft)] transition-[background,transform] hover:bg-brand-deep active:scale-95 focus-visible:outline-none"
        >
          {closed ? "Повторить" : "Разобрать"} →
        </button>
      </div>
    </article>
  );
}
