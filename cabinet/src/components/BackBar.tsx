import { useNavigate } from "react-router-dom";

interface Props {
  label?: string;
}

// Тихая строка возврата на хаб.
export default function BackBar({ label = "К срезу" }: Props) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate("/")}
      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-pill px-2 py-2.5 text-[14px] font-medium text-ink-soft transition hover:text-brand-deep focus-visible:outline-none"
    >
      ← {label}
    </button>
  );
}
