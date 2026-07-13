import type { ReactNode } from 'react'
import { ApBottomBar } from './ApBottomBar'

interface AppShellProps {
  children: ReactNode
}

// Оболочка v6: тёплая бумага В КЛЕТКУ (bg-graph — живая текстура тетради) на всю
// ширину, контент — колонка max-width 480 (canon §4), на ≥768 центрируется. Нижняя
// навигация ApBottomBar, safe-area учтена.
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="bg-graph relative min-h-dvh overflow-x-hidden">
      <div className="mx-auto flex min-h-dvh w-full max-w-[30rem] flex-col">
        <main
          className="flex-1 px-4 pb-28"
          style={{ paddingTop: 'max(1rem, env(safe-area-inset-top))' }}
        >
          {children}
        </main>
        <ApBottomBar />
      </div>
    </div>
  )
}
