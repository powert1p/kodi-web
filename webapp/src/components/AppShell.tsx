import type { ReactNode } from 'react'
import { ApBottomBar } from './ApBottomBar'

interface AppShellProps {
  children: ReactNode
}

// Оболочка AiPlus: белый фон (--bg-primary), мобильная колонка ~26rem, safe-area,
// нижняя навигация ApBottomBar. Плоско — глубина живёт в 1px-бордерах, не в фоне.
// Нижний отступ main учитывает фиксированный бар (последняя плитка не прячется).
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-bg-primary">
      <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col">
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
