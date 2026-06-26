import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
}

const ITEMS: NavItem[] = [
  {
    to: '/',
    label: 'Срез',
    icon: (
      <path d="M4 13h4v6H4zM10 6h4v13h-4zM16 9h4v10h-4z" />
    ),
  },
  {
    to: '/analytics',
    label: 'Прогресс',
    icon: <path d="M4 19 9 11l4 4 7-9M4 19h16" />,
  },
]

// Нижняя навигация. Тапабельные зоны ≥44px, safe-area снизу.
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 border-t border-line/60 bg-[color-mix(in_oklab,var(--color-base-2)_92%,transparent)] backdrop-blur-lg"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <ul className="mx-auto flex w-full max-w-[26rem] items-stretch justify-around px-4">
        {ITEMS.map((item) => (
          <li key={item.to} className="flex-1">
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'flex min-h-[3.25rem] flex-col items-center justify-center gap-1 text-[0.7rem] font-semibold transition-colors duration-200',
                  isActive ? 'text-brand' : 'text-ink-faint hover:text-ink-mute',
                ].join(' ')
              }
            >
              <svg
                viewBox="0 0 24 24"
                className="size-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                {item.icon}
              </svg>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
