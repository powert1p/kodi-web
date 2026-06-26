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
    icon: <path d="M4 13h4v6H4zM10 6h4v13h-4zM16 9h4v10h-4z" />,
  },
  {
    to: '/analytics',
    label: 'Прогресс',
    icon: <path d="M4 19 9 11l4 4 7-9M4 19h16" />,
  },
]

// Нижняя навигация — плавающая глиняная плашка. Тапабельные зоны ≥44px, safe-area снизу.
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20"
      style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
    >
      <ul className="clay mx-auto flex w-[calc(100%-2rem)] max-w-[24rem] items-stretch justify-around gap-2 rounded-(--radius-card) p-1.5">
        {ITEMS.map((item) => (
          <li key={item.to} className="flex-1">
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'press flex min-h-[3rem] flex-col items-center justify-center gap-1 rounded-(--radius-button) text-[0.72rem] font-extrabold',
                  isActive
                    ? 'bg-brand text-on-brand'
                    : 'text-ink-mute hover:bg-surface-muted hover:text-ink',
                ].join(' ')
              }
            >
              <svg
                viewBox="0 0 24 24"
                className="size-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
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
