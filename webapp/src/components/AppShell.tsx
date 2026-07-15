import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ApBottomBar } from './ApBottomBar'

interface AppShellProps { children: ReactNode }

export function AppShell({ children }: AppShellProps) {
  const { pathname } = useLocation()
  const isFocus = /^\/(drill|closure|srez|lesson)(\/|$)/.test(pathname)

  return (
    <div className="studio-grain relative min-h-dvh overflow-x-clip bg-paper text-text">
      <a
        href="#main-content"
        className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-control bg-brand px-4 py-3 text-title text-on-brand shadow-key transition-transform focus:translate-y-0"
      >
        К содержанию
      </a>
      {!isFocus && <ApBottomBar />}
      <main
        id="main-content"
        tabIndex={-1}
        className={[
          'min-h-dvh w-full',
          isFocus ? '' : 'pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0',
        ].join(' ')}
      >
        {children}
      </main>
    </div>
  )
}
