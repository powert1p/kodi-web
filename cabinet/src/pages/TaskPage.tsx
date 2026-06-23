import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { wrongTasks } from "../mock/srez";
import BackBar from "../components/BackBar";
import NotFoundTask from "../components/NotFoundTask";
import TaskPinnedCard from "../components/TaskPinnedCard";
import Ladder from "../components/ladder/Ladder";
import TutorSheet from "../components/tutor/TutorSheet";

// Экран разбора: закреплённая задача + «Лесенка понимания» + докнутая помощь.
export default function TaskPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tutorOpen, setTutorOpen] = useState(false);

  const task = wrongTasks.find((t) => t.id === id);
  if (!task) return <NotFoundTask />;

  return (
    <div className="pt-1">
      <div className="stagger space-y-4">
        <div className="flex items-center justify-between">
          <BackBar />
          <span className="font-num tabular text-[12px] text-muted">
            FR · {task.nodeId}
          </span>
        </div>

        <TaskPinnedCard task={task} />

        {/* key по задаче — пересоздаёт лесенку при переходе задача→задача,
            иначе стейт useLadder утекает с прошлой задачи (hash-навигация без перемонтирования) */}
        <Ladder
          key={task.id}
          task={task}
          onFinish={() => navigate(`/closure/${task.id}`)}
        />
      </div>

      {/* докнутая кнопка помощи — над safe-area, не перекрывает ступень */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 mx-auto flex max-w-[480px] justify-center px-4 pb-[max(env(safe-area-inset-bottom),14px)]">
        <button
          type="button"
          onClick={() => setTutorOpen(true)}
          className="pointer-events-auto inline-flex items-center gap-2 rounded-pill bg-ink/92 px-5 py-3 text-[14px] font-semibold text-white shadow-[var(--shadow-overlay)] backdrop-blur transition hover:bg-ink active:scale-95 focus-visible:outline-none"
        >
          <span aria-hidden>💬</span> Спросить помощь
        </button>
      </div>

      <TutorSheet open={tutorOpen} onClose={() => setTutorOpen(false)} />
    </div>
  );
}
