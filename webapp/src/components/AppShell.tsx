import type { ReactNode } from 'react'
import { ApBottomBar } from './ApBottomBar'

interface AppShellProps {
  children: ReactNode
}

// Оболочка v5: тёплая бумажная подложка (--paper) на всю ширину, контент —
// колонка max-width 480 (canon §4), на ≥768 центрируется на paper (не мобильная
// колонка во всю ширь планшета). Нижняя навигация ApBottomBar, safe-area учтена.
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-paper">
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
