import { NavLink } from 'react-router-dom'
import type { ComponentType } from 'react'
import { HomeIcon, HomeActiveIcon, TaskIcon, TaskActiveIcon } from '../icons'

interface IconProps {
  size?: number
}

interface NavItem {
  to: string
  label: string
  icon: ComponentType<IconProps>
  iconActive: ComponentType<IconProps>
  end?: boolean
}

const ITEMS: NavItem[] = [
  { to: '/', label: 'Срез', icon: HomeIcon, iconActive: HomeActiveIcon, end: true },
  { to: '/analytics', label: 'Прогресс', icon: TaskIcon, iconActive: TaskActiveIcon },
]

// ApBottomBar (v5) — мобильная навигация. Фон surface (белый — приподнят над
// paper-подложкой страницы), верхние углы радиус card, тень shadow-bottom-bar
// (единственная тень в системе), нижний паддинг = safe-area. Иконка 22, label.
//
// SIGNATURE: активная вкладка — иконка свапается outline→filled, цвет → brand,
// лёгкий scale ~1.15 (.ap-nav-icon в index.css). Единственная брендовая
// микро-анимация; остальной интерфейс держим тихим и плоским.
export function ApBottomBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 mx-auto w-full max-w-[30rem] rounded-t-card bg-surface"
      style={{
        boxShadow: 'var(--shadow-bottom-bar)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <ul className="flex items-stretch justify-around px-2">
        {ITEMS.map((item) => {
          const Icon = item.icon
          const IconActive = item.iconActive
          return (
            <li key={item.to} className="flex-1">
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    'flex min-h-12 flex-col items-center justify-center gap-1 py-2 text-label-small transition-colors',
                    isActive
                      ? 'ap-nav-active text-brand'
                      : 'text-text hover:text-brand',
                  ].join(' ')
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="ap-nav-icon">
                      {isActive ? <IconActive size={22} /> : <Icon size={22} />}
                    </span>
                    {item.label}
                  </>
                )}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
