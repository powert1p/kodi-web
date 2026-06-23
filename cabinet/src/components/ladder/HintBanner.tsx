import { motion } from "framer-motion";
import MathText from "../MathText";

interface Props {
  text: string;
}

// Сократическая подсказка после ошибки. Тёплая, не наказующая — без красного.
export default function HintBanner({ text }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-2.5 rounded-[14px] bg-spark-wash px-4 py-3 ring-1 ring-spark/20"
    >
      <span className="mt-0.5 text-[16px]" aria-hidden>
        💡
      </span>
      <p className="text-[14px] leading-relaxed text-ink-soft">
        <MathText>{text}</MathText>
      </p>
    </motion.div>
  );
}
