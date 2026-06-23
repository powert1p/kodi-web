import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import type { WrongTask } from "../../mock/srez";
import { useLadder } from "../../hooks/useLadder";
import { socraticHints, fallbackHint } from "../../mock/hints";
import Rung from "./Rung";
import RungInput from "./RungInput";
import RungOptions from "./RungOptions";
import HintBanner from "./HintBanner";

interface Props {
  task: WrongTask;
  onFinish: () => void;
}

// «Лесенка понимания» — signature-элемент. Управляет потоком ступеней,
// вставкой лёгкой ступени и climb-back, подсказками и завершением.
export default function Ladder({ task, onFinish }: Props) {
  const ladder = useLadder(task);
  const [wobble, setWobble] = useState(false);

  // Завершение лесенки → переход к закрытию (один раз)
  useEffect(() => {
    if (ladder.finished) {
      const t = setTimeout(onFinish, 700);
      return () => clearTimeout(t);
    }
  }, [ladder.finished, onFinish]);

  // Снимаем флаг вставки после анимации climb-down
  useEffect(() => {
    if (ladder.insertedKey) {
      const t = setTimeout(ladder.clearInserted, 600);
      return () => clearTimeout(t);
    }
  }, [ladder.insertedKey, ladder.clearInserted]);

  const handleSubmit = (value: string) => {
    const result = ladder.submit(value);
    if (result === "wrong") {
      setWobble(true);
      setTimeout(() => setWobble(false), 480);
    }
  };

  const active = ladder.rungs[ladder.activeIndex];

  // Прогрессивная подсказка: 1-я ошибка — концептуальный намёк (socratic);
  // 2-я ошибка — если у шага есть reveal, показываем расписанную арифметику.
  let hintText = "";
  if (active) {
    const concept = socraticHints[active.microSkill] ?? fallbackHint;
    hintText =
      ladder.attempts >= 2 && active.reveal ? active.reveal : concept;
  }

  return (
    <section aria-label="Лесенка понимания" className="space-y-3">
      <ol className="list-none">
        <AnimatePresence initial={false}>
          {ladder.rungs.map((rung, i) => (
            <Rung
              key={rung.key}
              rung={rung}
              index={i}
              isLast={i === ladder.rungs.length - 1}
              justInserted={rung.key === ladder.insertedKey}
            />
          ))}
        </AnimatePresence>
      </ol>

      {!ladder.finished && active && (
        <div className="space-y-2.5">
          <AnimatePresence>
            {ladder.showHint && (
              <HintBanner
                key={ladder.attempts >= 2 && active.reveal ? "reveal" : "concept"}
                text={hintText}
              />
            )}
          </AnimatePresence>
          {active.mode === "choose" && active.options ? (
            <RungOptions
              key={active.key}
              options={active.options}
              onSelect={handleSubmit}
              wobble={wobble}
            />
          ) : (
            <RungInput onSubmit={handleSubmit} wobble={wobble} />
          )}
        </div>
      )}

      {ladder.finished && (
        <p className="rounded-[14px] bg-got-wash px-4 py-3 text-center text-[14px] font-semibold text-got ring-1 ring-got/25">
          Вся лесенка пройдена — закрепим проверкой ✦
        </p>
      )}
    </section>
  );
}
