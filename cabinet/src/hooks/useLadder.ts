import { useMemo, useState } from "react";
import type { WrongTask, StepOption } from "../mock/srez";
import { easierPool } from "../mock/srez";
import { answersMatch } from "../lib/math";

// Тип ступени лесенки: оригинальная или вставленная «попроще».
export type RungKind = "original" | "easier";
export type RungStatus = "locked" | "active" | "solved";
// Способ ответа на ступени: ввод числа или выбор варианта.
export type RungAnswerMode = "compute" | "choose";

export interface Rung {
  key: string;
  kind: RungKind;
  instruction: string;
  microSkill: string;
  expected: string; // для "compute" — ответ; для "choose" — id верного варианта
  status: RungStatus;
  // Расширение для текстовых задач:
  mode: RungAnswerMode; // как отвечать
  options?: StepOption[]; // варианты для "choose"
  reveal?: string; // расписанная арифметика — только как глубокая подсказка
  parentKey?: string; // для easier — ключ ступени, к которой возвращаемся
}

export interface LadderApi {
  rungs: Rung[];
  activeIndex: number;
  attempts: number; // попытки на текущей ступени
  showHint: boolean;
  insertedKey: string | null; // ключ только что вставленной лёгкой ступени (для анимации climb)
  finished: boolean;
  submit: (value: string) => "correct" | "wrong" | "inserted";
  clearInserted: () => void;
}

// Сравнение ответа со ступенью: "choose" — точный id, "compute" — нормализация.
function rungMatches(rung: Rung, value: string): boolean {
  if (rung.mode === "choose") return value === rung.expected;
  return answersMatch(value, rung.expected);
}

// Строим стартовый набор ступеней из шагов задачи.
function buildInitial(task: WrongTask): Rung[] {
  return task.steps.map((s, i) => ({
    key: `s${s.n}`,
    kind: "original" as const,
    instruction: s.instruction,
    microSkill: s.microSkill,
    expected: s.expected,
    status: i === 0 ? "active" : "locked",
    mode: s.kind ?? "compute",
    options: s.options,
    reveal: s.reveal,
  }));
}

export function useLadder(task: WrongTask): LadderApi {
  const [rungs, setRungs] = useState<Rung[]>(() => buildInitial(task));
  const [attempts, setAttempts] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [insertedKey, setInsertedKey] = useState<string | null>(null);

  const activeIndex = useMemo(
    () => rungs.findIndex((r) => r.status === "active"),
    [rungs],
  );
  const finished = activeIndex === -1 && rungs.every((r) => r.status === "solved");

  const submit = (value: string): "correct" | "wrong" | "inserted" => {
    if (activeIndex === -1) return "wrong";
    const active = rungs[activeIndex];

    if (rungMatches(active, value)) {
      // Решено: гасим текущую, активируем следующую
      setRungs((prev) => {
        const next = prev.map((r, i) =>
          i === activeIndex ? { ...r, status: "solved" as RungStatus } : r,
        );
        const nextIdx = next.findIndex((r) => r.status === "locked");
        if (nextIdx !== -1) next[nextIdx] = { ...next[nextIdx], status: "active" };
        return next;
      });
      setAttempts(0);
      setShowHint(false);
      return "correct";
    }

    // Неверно
    const newAttempts = attempts + 1;
    setAttempts(newAttempts);
    setShowHint(true);

    // Вторая ошибка на оригинальной ступени.
    // Приоритет помощи при затыке (как просил владелец):
    // 1-я ошибка → подсказка-вопрос (Ladder показывает по attempts).
    // 2-я ошибка → даём задачу ПОПРОЩЕ (climb-down), если она есть в easierPool
    //   и для этой ступени ещё не давалась.
    // Если попроще нет / уже давали → остаётся reveal (расписанная арифметика),
    //   который Ladder показывает по attempts≥2 при наличии reveal.
    const alreadyEasier = rungs.some((r) => r.parentKey === active.key);
    if (newAttempts >= 2 && active.kind === "original" && !alreadyEasier) {
      const easier = easierPool[active.microSkill];
      if (easier) {
        const easierRung: Rung = {
          key: `${active.key}-easy`,
          kind: "easier",
          instruction: easier.instruction,
          microSkill: easier.microSkill,
          expected: easier.expected,
          status: "active",
          mode: "compute",
          parentKey: active.key,
        };
        setRungs((prev) => {
          // текущая оригинальная → locked (climb back позже), вставляем easier перед ней
          const next = prev.map((r, i) =>
            i === activeIndex ? { ...r, status: "locked" as RungStatus } : r,
          );
          next.splice(activeIndex, 0, easierRung);
          return next;
        });
        setInsertedKey(easierRung.key);
        setAttempts(0);
        setShowHint(false);
        return "inserted";
      }
    }

    // Если решена вставленная лёгкая ступень — climb back обрабатывается в ветке "correct"
    return "wrong";
  };

  const clearInserted = () => setInsertedKey(null);

  return {
    rungs,
    activeIndex,
    attempts,
    showHint,
    insertedKey,
    finished,
    submit,
    clearInserted,
  };
}
