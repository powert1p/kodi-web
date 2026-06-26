import type { ReactNode } from 'react'
import { BottomNav } from './BottomNav'

interface AppShellProps {
  children: ReactNode
}

// Оболочка: тёмный слоёный фон (глубина светлотой, не плоская заливка),
// мобильная колонка 390px, safe-area, нижняя навигация.
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      {/* Слоёный фон-градиент — не плоский цвет */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-base"
      />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(120%_60%_at_50%_-10%,color-mix(in_oklab,var(--color-brand)_22%,transparent),transparent_60%),radial-gradient(90%_50%_at_90%_100%,color-mix(in_oklab,var(--color-revisit)_12%,transparent),transparent_55%)]"
      />

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
