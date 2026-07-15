import { useEffect, useRef } from 'react'
import type { Rung } from '../../lib/ladder'
import { CheckIcon } from '../../icons'
import { RungActive } from './RungActive'
import { RungSolved, RungLocked } from './RungQuiet'

interface LadderProps {
  rungs: readonly Rung[]
  hint: boolean
  hintText?: string | null
  showReveal: boolean
  insertedKey: string | null
  photoMode?: boolean
  hideLocked?: boolean
  checking?: boolean
  onSubmit: (value: string) => void | Promise<void>
}

export function Ladder({ rungs, hint, hintText, showReveal, insertedKey, photoMode, hideLocked = false, checking = false, onSubmit }: LadderProps) {
  let originalCounter = 0
  const numbered = rungs.map((rung) => {
    if (rung.kind === 'original') originalCounter += 1
    return { rung, num: originalCounter }
  })
  const activeKey = rungs.find((rung) => rung.status === 'active')?.key ?? null
  const previousActiveKey = useRef(activeKey)
  const focusActive = previousActiveKey.current !== null && previousActiveKey.current !== activeKey

  useEffect(() => { previousActiveKey.current = activeKey }, [activeKey])

  return (
    <div className="min-w-0">
      <div className="mb-4 flex items-center justify-between gap-4 border-b border-ink/15 pb-4">
        <div>
          <p className="text-mark text-brand-deep">Лента решения</p>
          <p className="mt-2 hidden text-caption1 text-muted sm:block">Верный шаг защёлкивается и открывает следующий.</p>
        </div>
      </div>
      <ol className="solution-ladder min-w-0">
        {numbered.filter(({ rung }) => !hideLocked || rung.status !== 'locked').map(({ rung, num }) => (
          <li key={rung.key} className="solution-ladder__item">
            <span
              className={[
                'solution-ladder__node',
                rung.status === 'active' ? 'solution-ladder__node--active' : '',
                rung.status === 'solved' ? 'solution-ladder__node--done' : '',
              ].filter(Boolean).join(' ')}
              aria-hidden
            >
              {rung.status === 'solved' ? <CheckIcon size={12} /> : String(Math.max(1, num)).padStart(2, '0')}
            </span>
            <div className="min-w-0">
              {rung.status === 'active' ? (
                <RungActive
                  rung={rung}
                  index={num}
                  hint={hint}
                  hintText={hintText}
                  showReveal={showReveal}
                  justInserted={rung.key === insertedKey}
                  focusOnMount={focusActive}
                  photoMode={photoMode}
                  checking={checking}
                  onSubmit={onSubmit}
                />
              ) : rung.status === 'solved' ? (
                <RungSolved rung={rung} index={num} />
              ) : (
                <RungLocked rung={rung} index={num} />
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
