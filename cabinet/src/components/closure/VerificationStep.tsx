import { useState } from "react";
import type { Verification } from "../../mock/srez";
import { answersMatch } from "../../lib/math";
import MathText from "../MathText";
import RungInput from "../ladder/RungInput";
import { socraticHints, fallbackHint } from "../../mock/hints";
import HintBanner from "../ladder/HintBanner";

interface Props {
  verification: Verification;
  microSkill: string;
  onPass: () => void;
}

// Финальная проверка закрытия: одна свежая задача (другие числа), подсказки-«мягко».
export default function VerificationStep({
  verification,
  microSkill,
  onPass,
}: Props) {
  const [wobble, setWobble] = useState(false);
  const [showHint, setShowHint] = useState(false);

  const handle = (value: string) => {
    if (answersMatch(value, verification.expected)) {
      onPass();
      return;
    }
    setWobble(true);
    setShowHint(true);
    setTimeout(() => setWobble(false), 480);
  };

  return (
    <section className="space-y-3">
      <div className="graph-paper rounded-[16px] bg-card p-5 shadow-[var(--shadow-raised)] ring-1 ring-brand/20">
        <p className="text-[12px] font-semibold uppercase tracking-wider text-brand-deep">
          Проверка понимания
        </p>
        <p className="mt-2 text-[17px] leading-relaxed text-ink">
          <MathText>{verification.statement}</MathText>
        </p>
      </div>

      {showHint && (
        <HintBanner text={socraticHints[microSkill] ?? fallbackHint} />
      )}

      <RungInput onSubmit={handle} wobble={wobble} />
    </section>
  );
}
