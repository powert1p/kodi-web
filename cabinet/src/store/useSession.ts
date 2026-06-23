import { create } from "zustand";
import { wrongTasks } from "../mock/srez";

// Сессионное состояние разбора среза.
// Какие задачи уже закрыты (освоены через закрытие) — двигает счётчик хаба.

interface SessionState {
  // id задач, которые ученик уже разобрал и подтвердил на закрытии
  closedIds: string[];
  // флаг «идёт загрузка хаба» — имитируем сетевой фетч один раз
  loaded: boolean;
  setLoaded: (v: boolean) => void;
  closeTask: (id: string) => void;
  isClosed: (id: string) => boolean;
  remaining: () => number;
  reset: () => void;
}

const TOTAL = wrongTasks.length;

export const useSession = create<SessionState>((set, get) => ({
  closedIds: [],
  loaded: false,
  setLoaded: (v) => set({ loaded: v }),
  closeTask: (id) =>
    set((s) =>
      s.closedIds.includes(id)
        ? s
        : { closedIds: [...s.closedIds, id] },
    ),
  isClosed: (id) => get().closedIds.includes(id),
  remaining: () => TOTAL - get().closedIds.length,
  reset: () => set({ closedIds: [], loaded: false }),
}));

export const TOTAL_ERRORS = TOTAL;
