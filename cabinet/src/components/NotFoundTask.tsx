import { useNavigate } from "react-router-dom";
import BackBar from "./BackBar";

// Состояние ошибки уровня страницы: задача не найдена. С действием-возвратом.
export default function NotFoundTask() {
  const navigate = useNavigate();
  return (
    <div className="pt-2">
      <BackBar />
      <div className="mt-6 rounded-[20px] bg-card p-8 text-center shadow-[var(--shadow-soft)] ring-1 ring-line">
        <p className="text-[40px]" aria-hidden>
          🧭
        </p>
        <h2 className="font-display text-[20px] font-bold text-ink mt-2">
          Эта задача не нашлась
        </h2>
        <p className="text-[14px] text-ink-soft mt-1.5">
          Вернёмся к срезу и выберем другую.
        </p>
        <button
          type="button"
          onClick={() => navigate("/")}
          className="mt-5 rounded-pill bg-brand px-5 py-2.5 text-[14px] font-semibold text-white shadow-[var(--shadow-soft)] transition hover:bg-brand-deep active:scale-95 focus-visible:outline-none"
        >
          К срезу
        </button>
      </div>
    </div>
  );
}
