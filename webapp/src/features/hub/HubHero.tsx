import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApButton } from '../../components/ApButton'
import { KodiBubble } from '../../components/KodiBubble'
import { RightIcon } from '../../icons'
import { ProgressBar } from './ProgressBar'
import heroDesk from '../../assets/hero-desk.jpg'

interface HubHeroProps {
  /** Всего ошибок в срезе. */
  total: number
  /** Сколько уже «готово». */
  done: number
  /** id самой приоритетной ошибки — цель единственного primary-CTA экрана. */
  firstTaskId: string | null
}

// Трейлхед маршрута: тёплая полоса-иллюстрация мастерской со сплошным scrim (AA §10),
// ЧИСЛО-ГЕРОЙ (Unbounded-гигант) — и маршрут СТАРТУЕТ прямо под ним: узел у основания
// цифры, живой штрих ныряет вниз-влево мимо CTA и выходит к рельсу списка ниже (R3 §1
// «первый изгиб заходит в hero, стартовая точка под числом-героем»). Голос Кёди (hi §7),
// честный прогресс, единственный primary-CTA «Разобрать первую» — без скролла.
export function HubHero({ total, done, firstTaskId }: HubHeroProps) {
  const navigate = useNavigate()
  const remaining = Math.max(total - done, 0)
  const allDone = remaining === 0

  const heroRef = useRef<HTMLElement>(null)
  const numRef = useRef<HTMLSpanElement>(null)
  const drawRef = useRef<SVGPathElement>(null)
  // Геометрия запуска маршрута: box hero + центр-низ числа-героя (измеряем, т.к.
  // clamp-кегль зависит от вьюпорта, а число бывает 1-2 знака).
  const [geo, setGeo] = useState<{ w: number; h: number; nx: number; ny: number } | null>(null)

  useEffect(() => {
    if (allDone) return
    const hero = heroRef.current
    const num = numRef.current
    if (!hero || !num) return
    const measure = () => {
      const hb = hero.getBoundingClientRect()
      const nb = num.getBoundingClientRect()
      setGeo({
        w: Math.max(1, Math.ceil(hb.width)),
        h: Math.max(1, Math.ceil(hb.height)),
        nx: nb.left - hb.left + 10, // чуть внутри левой стойки цифры
        ny: nb.bottom - hb.top - 10, // у основания глифа
      })
    }
    const raf = requestAnimationFrame(measure)
    if (document.fonts?.ready) void document.fonts.ready.then(() => requestAnimationFrame(measure))
    let ro: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure)
      ro.observe(hero)
    }
    return () => {
      cancelAnimationFrame(raf)
      ro?.disconnect()
    }
  }, [allDone, remaining])

  // Draw штриха запуска поверх подложки (reduced-motion → мгновенно).
  useEffect(() => {
    const p = drawRef.current
    if (!p || !geo) return
    const reduce =
      typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      p.style.strokeDasharray = ''
      p.style.strokeDashoffset = '0'
      return
    }
    let len = 0
    try {
      len = p.getTotalLength()
    } catch {
      len = geo.h
    }
    p.style.transition = 'none'
    p.style.strokeDasharray = String(len)
    p.style.strokeDashoffset = String(len)
    void p.getBoundingClientRect()
    p.style.transition = 'stroke-dashoffset 1s var(--ease-out-soft) 0.25s'
    p.style.strokeDashoffset = '0'
  }, [geo])

  // Кривая запуска: от узла под числом (nx,ny) уверенным штрихом ныряет вниз-влево к
  // рельсу списка (x=22) у нижней кромки hero — стыкуется со stroke-подложкой RouteSpine
  // ниже (тот же x). Один плавный cubic — «маркер провёл от цифры вниз».
  const launch = geo
    ? `M ${geo.nx} ${geo.ny} C ${geo.nx - 22} ${geo.ny + 38}, 23 ${geo.ny + (geo.h - geo.ny) * 0.46}, 22 ${geo.h - 2}`
    : ''

  return (
    <section ref={heroRef} className="relative -mt-1 overflow-hidden rounded-card border border-stroke">
      {/* Иллюстрация мастерской + сплошной тёплый scrim под текстом (AA) */}
      <img
        src={heroDesk}
        alt=""
        aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-90"
      />
      <div className="hero-scrim pointer-events-none absolute inset-0" />

      {/* Запуск маршрута: след-подложка + прочерченный штрих + узел-трейлхед под числом */}
      {geo && launch && (
        <svg
          className="pointer-events-none absolute inset-0 overflow-visible"
          width={geo.w}
          height={geo.h}
          viewBox={`0 0 ${geo.w} ${geo.h}`}
          aria-hidden
        >
          <path d={launch} fill="none" stroke="var(--route-trace)" strokeWidth={2.5} strokeLinecap="round" />
          <path
            ref={drawRef}
            d={launch}
            fill="none"
            stroke="var(--route-line)"
            strokeWidth={5.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx={geo.nx} cy={geo.ny} r={7} fill="var(--brand)" stroke="var(--surface)" strokeWidth={2} />
        </svg>
      )}

      <div className="relative flex flex-col gap-4 p-4 pl-9">
        <p className="text-caption1-medium uppercase tracking-[0.14em] text-brand-ink">
          Срез на сегодня
        </p>

        {allDone ? (
          <h1 className="text-h1 text-ink">Всё разобрано!</h1>
        ) : (
          <h1 className="flex items-end gap-3">
            <span ref={numRef} className="text-hero text-ink">
              {remaining}
            </span>
            <span className="text-h1 pb-2 text-ink">{plural(remaining)}</span>
          </h1>
        )}

        <KodiBubble mood={allDone ? 'celebrate' : 'hi'} size="s">
          {allDone
            ? 'Ни одной незакрытой ошибки — чисто. Можно закреплять победы.'
            : 'Привет! Я рядом. Начнём с первой — она сегодня главная, дальше будет легче.'}
        </KodiBubble>

        <ProgressBar done={done} total={total} />

        {!allDone && firstTaskId && (
          <ApButton
            variant="primary"
            size="l"
            full
            onClick={() => navigate(`/drill/${firstTaskId}`)}
          >
            Разобрать первую
            <RightIcon size={18} />
          </ApButton>
        )}
      </div>
    </section>
  )
}

// Склонение «ошибка» для русского счётчика (с глаголом «ждёт/ждут»).
function plural(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'ошибка ждёт'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'ошибки ждут'
  return 'ошибок ждут'
}
