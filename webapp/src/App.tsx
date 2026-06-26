import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { HubPage } from './features/hub/HubPage'
import { DrillPage } from './features/drill/DrillPage'
import { PlaceholderPage } from './features/placeholder/PlaceholderPage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HubPage />} />
        <Route path="/drill/:taskId" element={<DrillPage />} />
        <Route
          path="/closure/:taskId"
          element={
            <PlaceholderPage
              title="Закрепление"
              note="Контрольная задача на тот же навык — скоро."
            />
          }
        />
        <Route
          path="/analytics"
          element={
            <PlaceholderPage
              title="Прогресс"
              note="Карта роста по навыкам появится здесь."
            />
          }
        />
      </Routes>
    </AppShell>
  )
}

export default App
