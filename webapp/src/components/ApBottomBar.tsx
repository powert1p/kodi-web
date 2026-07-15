import { NavLink } from 'react-router-dom'
import type { ComponentType } from 'react'
import { TaskIcon, BarsTabIcon } from '../icons'
import { BrandMark } from './BrandMark'

interface IconProps { size?: number }
interface NavItem { to: string; label: string; icon: ComponentType<IconProps>; end?: boolean }

const ITEMS: NavItem[] = [
  { to: '/', label: 'Путь', icon: TaskIcon, end: true },
  { to: '/analytics', label: 'Прогресс', icon: BarsTabIcon },
]

export function ApBottomBar() {
  return (
    <>
      <header className="relative z-40 bg-transparent">
        <div className="mx-auto flex min-h-18 max-w-[90rem] items-center justify-between px-5 md:px-8">
          <BrandMark />
          <nav aria-label="Основная навигация" className="hidden items-center gap-1 md:flex">
            {ITEMS.map((item) => <DesktopLink key={item.to} item={item} />)}
          </nav>
          <span className="hidden rounded-chip border border-ink/15 bg-surface/70 px-3 py-2 text-right text-caption2-medium text-muted lg:block">
            один точный шаг за раз
          </span>
        </div>
      </header>

      <nav
        aria-label="Основная навигация"
        className="fixed inset-x-0 bottom-0 z-50 border-t border-ink/10 bg-surface/90 shadow-bottom-bar backdrop-blur-xl md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <ul className="grid grid-cols-2">
          {ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => [
                    'relative flex min-h-16 items-center justify-center gap-2 px-3 text-label-small transition-colors',
                    isActive
                      ? 'text-ink before:absolute before:top-0 before:h-1 before:w-8 before:rounded-b-full before:bg-brand'
                      : 'text-muted hover:bg-sage-soft hover:text-ink',
                  ].join(' ')}
                >
                  <Icon size={19} />
                  {item.label}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>
    </>
  )
}

function DesktopLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => [
        'relative inline-flex min-h-11 items-center gap-2 rounded-chip px-5 text-caption1-medium transition-colors',
        isActive
          ? 'bg-surface text-ink shadow-lift-sm after:absolute after:bottom-1 after:h-1 after:w-6 after:rounded-full after:bg-brand'
          : 'text-muted hover:bg-sage-soft hover:text-ink',
      ].join(' ')}
    >
      <Icon size={18} />
      {item.label}
    </NavLink>
  )
}
