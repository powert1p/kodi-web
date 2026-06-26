import type { ReactNode } from 'react'
import { BottomNav } from './BottomNav'

interface AppShellProps {
  children: ReactNode
}

// Оболочка: тёплый кремовый фон, мобильная колонка ~26rem, safe-area,
// нижняя навигация. Чисто и плоско — глубина живёт в 3D-кнопках, не в фоне.
// Нижний отступ main учитывает фиксированную навигацию (последняя плитка не прячется).
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-bg">
      <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col">
        <main
          className="flex-1 px-4 pb-28"
          style={{ paddingTop: 'max(1rem, env(safe-area-inset-top))' }}
        >
          {children}
        </main>
        <BottomNav />
      </div>
    </div>
  )
}
