import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { clearToken } from '../lib/auth'
import { ApBottomBar } from './ApBottomBar'

interface AppShellProps { children: ReactNode }

export function AppShell({ children }: AppShellProps) {
  const { pathname } = useLocation()
  const isFocus = pathname === '/' || /^\/(drill|closure|srez|lesson)(\/|$)/.test(pathname)

  return (
    <div className="studio-grain relative min-h-dvh overflow-x-clip bg-paper text-text">
      <a
        href="#main-content"
        className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-control bg-brand px-4 py-3 text-title text-on-brand shadow-key focus-visible:translate-y-0"
      >
        К содержанию
      </a>
      <button
        type="button"
        onClick={clearToken}
        aria-label="Сменить ученика"
        title="Выйти и войти как другой ученик"
        className="fixed right-[max(0.875rem,env(safe-area-inset-right))] top-[max(0.625rem,env(safe-area-inset-top))] z-[60] inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-full border border-line/70 bg-paper/90 px-3 text-sm font-bold text-muted shadow-key backdrop-blur transition hover:border-brand/45 hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 sm:px-4"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8">
          <path d="M10 5H6.8A1.8 1.8 0 0 0 5 6.8v10.4A1.8 1.8 0 0 0 6.8 19H10" />
          <path d="m14.5 8 4 4-4 4M18.5 12H9" />
        </svg>
        <span className="hidden sm:inline">Сменить ученика</span>
      </button>
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
