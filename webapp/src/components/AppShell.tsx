import type { ReactNode } from 'react'
import { BottomNav } from './BottomNav'

interface AppShellProps {
  children: ReactNode
}

// Оболочка: светлый «глиняный» фон с мягким голубым градиентом и медленно
// дрейфующими декоративными блобами (reduced-motion безопасно). Мобильная
// колонка 26rem, safe-area, нижняя навигация.
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      {/* Базовый мягкий градиент (не плоская заливка) */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-20 bg-[linear-gradient(180deg,var(--color-bg),var(--color-bg-2))]"
      />
      {/* Дрейфующие кэнди-блобы — атмосфера, не декор поверх контента */}
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="blob absolute -left-24 -top-20 size-72 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--color-brand)_22%,transparent),transparent_70%)] blur-2xl" />
        <div className="blob-2 absolute -right-24 top-1/3 size-80 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--color-pink)_16%,transparent),transparent_70%)] blur-2xl" />
        <div className="blob absolute -bottom-24 left-1/4 size-72 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--color-amber)_16%,transparent),transparent_70%)] blur-2xl" />
      </div>

      <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col">
        <main
          className="flex-1 px-4 pb-28"
          style={{ paddingTop: 'max(1.25rem, env(safe-area-inset-top))' }}
        >
          {children}
        </main>
        <BottomNav />
      </div>
    </div>
  )
}
