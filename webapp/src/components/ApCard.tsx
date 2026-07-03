import type { ComponentPropsWithoutRef, ElementType, ReactNode } from 'react'

// ApCard (DESIGN_SYSTEM §3 — контракт закрыт: tone/padding). Плоская bordered-карточка,
// БЕЗ тени — глубина живёт в поверхности+бордере. tone=surface — обычная белая
// карточка (эталон: список ошибок/скелетоны). tone=brand-soft — ЕДИНСТВЕННЫЙ
// активный фокус экрана (эталон: HubHero, активная ступень лесенки) — не размножать.
// success-soft/attn-soft — закрытие темы / «не сошлось» (§5).
// Полиморфна через `as` (article/section/button) — карточка иногда САМА тапается
// (TaskCard), тогда a11y/touch-target остаются на нативном <button>.

export type CardTone = 'surface' | 'brand-soft' | 'success-soft' | 'attn-soft'
type Padding = 'm' | 'l'

const TONE: Record<CardTone, string> = {
  surface: 'bg-surface border-stroke',
  'brand-soft': 'bg-brand-soft border-brand/30',
  'success-soft': 'bg-success-soft border-success/30',
  'attn-soft': 'bg-attn-soft border-attn/30',
}

const PADDING: Record<Padding, string> = {
  m: 'p-4',
  l: 'p-6',
}

type ApCardOwnProps<T extends ElementType> = {
  as?: T
  tone?: CardTone
  padding?: Padding
  children: ReactNode
  className?: string
}

type ApCardProps<T extends ElementType> = ApCardOwnProps<T> &
  Omit<ComponentPropsWithoutRef<T>, keyof ApCardOwnProps<T>>

export function ApCard<T extends ElementType = 'div'>({
  as,
  tone = 'surface',
  padding = 'm',
  children,
  className = '',
  ...rest
}: ApCardProps<T>) {
  const Tag = (as ?? 'div') as ElementType
  return (
    <Tag
      className={[
        'rounded-card border',
        TONE[tone],
        PADDING[padding],
        className,
      ].join(' ')}
      {...rest}
    >
      {children}
    </Tag>
  )
}
