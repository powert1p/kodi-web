import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { wrongTasks, verifications } from "../mock/srez";
import { useSession, TOTAL_ERRORS } from "../store/useSession";
import BackBar from "../components/BackBar";
import NotFoundTask from "../components/NotFoundTask";
import VerificationStep from "../components/closure/VerificationStep";
import Celebration from "../components/closure/Celebration";

// Закрытие: одна свежая проверка → праздник + метр освоения.
// На успехе уменьшаем счётчик среза. Достигли 0 → самый большой праздник.
export default function ClosurePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const closeTask = useSession((s) => s.closeTask);
  const closedIds = useSession((s) => s.closedIds);
  const [passed, setPassed] = useState(false);

  const task = wrongTasks.find((t) => t.id === id);
  if (!task) return <NotFoundTask />;

  // Подбираем проверку по узлу задачи (фолбэк — первая)
  const verification =
    verifications[task.nodeId] ?? Object.values(verifications)[0];

  // Сколько останется ПОСЛЕ закрытия этой задачи
  const willBeClosed = closedIds.includes(task.id)
    ? closedIds.length
    : closedIds.length + 1;
  const remainingAfter = TOTAL_ERRORS - willBeClosed;
  const biggest = remainingAfter <= 0;

  const handlePass = () => {
    closeTask(task.id);
    setPassed(true);
  };

  return (
    <div className="pt-1">
      {!passed && (
        <div className="stagger space-y-4">
          <BackBar />
          <div className="rounded-[16px] bg-got-wash px-4 py-3 ring-1 ring-got/25">
            <p className="text-[14px] font-semibold text-got">
              Лесенка пройдена ✓
            </p>
            <p className="text-[13px] text-ink-soft mt-0.5">
              Закрепим на похожей задаче — без подсказок по умолчанию.
            </p>
          </div>
          <VerificationStep
            verification={verification}
            microSkill={task.primaryMicroSkill}
            onPass={handlePass}
          />
        </div>
      )}

      {passed && (
        <div className="pt-6">
          <Celebration
            biggest={biggest}
            remaining={remainingAfter}
            onContinue={() => navigate("/")}
          />
        </div>
      )}
    </div>
  );
}
