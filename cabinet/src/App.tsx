import { Routes, Route } from "react-router-dom";
import HubPage from "./pages/HubPage";
import TaskPage from "./pages/TaskPage";
import ClosurePage from "./pages/ClosurePage";

// Корневая оболочка: одна центрированная колонка ~480px на слоистом фоне.
// Mobile-first — на широких экранах колонка просто центрируется.
export default function App() {
  return (
    <div className="min-h-full w-full flex justify-center">
      <div className="w-full max-w-[480px] px-4 pb-24 pt-3">
        <Routes>
          <Route path="/" element={<HubPage />} />
          <Route path="/task/:id" element={<TaskPage />} />
          <Route path="/closure/:id" element={<ClosurePage />} />
        </Routes>
      </div>
    </div>
  );
}
