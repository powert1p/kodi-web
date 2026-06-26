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

// Нижняя навигация — плоская белая плашка с тонким тёплым бордером.
// Активная вкладка подсвечена оранжевым. Тап-зоны ≥44px, safe-area снизу.
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20"
      style={{ paddingBottom: 'max(0.625rem, env(safe-area-inset-bottom))' }}
    >
      <ul className="card-flat mx-auto flex w-[calc(100%-2rem)] max-w-[24rem] items-stretch justify-around gap-2 rounded-(--radius-card) p-1.5">
        {ITEMS.map((item) => (
          <li key={item.to} className="flex-1">
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'flex min-h-12 flex-col items-center justify-center gap-1 rounded-(--radius-button) text-[0.72rem] font-extrabold transition-colors',
                  isActive
                    ? 'bg-primary text-on-primary'
                    : 'text-ink-mute hover:bg-surface-soft hover:text-primary-ink',
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
