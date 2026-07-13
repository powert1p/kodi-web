import { NavLink } from 'react-router-dom'
import type { ComponentType } from 'react'
import { RouteTabIcon, BarsTabIcon } from '../icons'

interface IconProps {
  size?: number
}

interface NavItem {
  to: string
  label: string
  icon: ComponentType<IconProps>
  end?: boolean
}

const ITEMS: NavItem[] = [
  { to: '/', label: 'Срез', icon: RouteTabIcon, end: true },
  { to: '/analytics', label: 'Прогресс', icon: BarsTabIcon },
]

// ApBottomBar (v6) — мобильная навигация. Фон surface (приподнят над клеткой),
// верхние углы радиус card, тень bottom-bar, нижний паддинг = safe-area.
//
// SIGNATURE §9: активная вкладка — часть маршрута. Иконка — язык пути (восходящий
// маршрут / столбцы прогресса, НЕ генерик home/list); активная → brand-ink + лёгкий
// scale + брендовая ОТМЕТКА-точка маршрута под лейблом. Оранж бережём: неактивные — label.
export function ApBottomBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 mx-auto w-full max-w-[30rem] rounded-t-card border-t border-stroke bg-surface"
      style={{
        boxShadow: 'var(--shadow-bottom-bar)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <ul className="flex items-stretch justify-around px-2">
        {ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <li key={item.to} className="flex-1">
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    'flex min-h-12 flex-col items-center justify-center gap-1 py-2 text-label-small transition-colors',
                    isActive
                      ? 'ap-nav-active text-brand-ink'
                      : 'text-label hover:text-brand-ink',
                  ].join(' ')
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="ap-nav-icon">
                      <Icon size={22} />
                    </span>
                    {item.label}
                    {/* Отметка-точка маршрута под активной вкладкой */}
                    <span
                      aria-hidden
                      className={[
                        'h-1 w-1 rounded-full bg-brand transition-opacity',
                        isActive ? 'opacity-100' : 'opacity-0',
                      ].join(' ')}
                    />
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
