import type { TutorMessage } from "../../mock/tutor";
import MathText from "../MathText";

interface Props {
  msg: TutorMessage;
}

// Пузырь чата тьютора/ученика. Контент через KaTeX-рендер.
export default function ChatBubble({ msg }: Props) {
  const tutor = msg.from === "tutor";
  return (
    <div className={`flex ${tutor ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[82%] rounded-[16px] px-3.5 py-2.5 text-[14px] leading-relaxed ${
          tutor
            ? "bg-brand-wash text-ink ring-1 ring-brand/10 rounded-bl-[6px]"
            : "bg-brand text-white rounded-br-[6px]"
        }`}
      >
        <MathText>{msg.text}</MathText>
      </div>
    </div>
  );
}
