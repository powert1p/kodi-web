import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { wrongTasks } from "../mock/srez";
import { useSession, TOTAL_ERRORS } from "../store/useSession";
import HubHeader from "../components/HubHeader";
import StreakRow from "../components/StreakRow";
import TaskTile from "../components/TaskTile";
import { HubSkeleton } from "../components/Skeleton";
import EmptyAllClear from "../components/EmptyAllClear";

// Срез-хаб: шапка-прогресс + список ошибочных задач в цветах семафора.
// Закрытая задача уезжает из списка (animate off), кольцо считает N→total.
export default function HubPage() {
  const loaded = useSession((s) => s.loaded);
  const setLoaded = useSession((s) => s.setLoaded);
  const closedIds = useSession((s) => s.closedIds);

  // Имитация одноразового сетевого фетча хаба
  useEffect(() => {
    if (loaded) return;
    const t = setTimeout(() => setLoaded(true), 650);
    return () => clearTimeout(t);
  }, [loaded, setLoaded]);

  const done = closedIds.length;
  const open = wrongTasks.filter((t) => !closedIds.includes(t.id));
  const allClear = done >= TOTAL_ERRORS;

  if (!loaded) {
    return (
      <main className="pt-1">
        <HubSkeleton />
      </main>
    );
  }

  return (
    <main className="stagger space-y-4 pt-1">
      <HubHeader done={done} total={TOTAL_ERRORS} />
      <StreakRow />

      {allClear ? (
        <EmptyAllClear />
      ) : (
        <>
          <div className="flex items-baseline justify-between px-1">
            <h2 className="font-display text-[17px] font-semibold text-ink">
              Где растёт мозг
            </h2>
            <span className="font-num tabular text-[13px] text-muted">
              {open.length} в работе
            </span>
          </div>

          <div className="space-y-3">
            <AnimatePresence mode="popLayout">
              {open.map((task) => (
                <motion.div
                  key={task.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: 40, scale: 0.96 }}
                  transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
                >
                  <TaskTile task={task} closed={false} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </>
      )}
    </main>
  );
}
