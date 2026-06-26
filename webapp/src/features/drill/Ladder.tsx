import type { Rung } from '../../lib/ladder'
import { RungActive } from './RungActive'
import { RungSolved, RungLocked } from './RungQuiet'

interface LadderProps {
  rungs: readonly Rung[]
  hint: boolean
  showReveal: boolean
  /** Ключ ступени, вставленной последней (для тона баннера climb-down). */
  insertedKey: string | null
  onSubmit: (value: string) => void
}

// SIGNATURE: вертикальная лесенка с непрерывным «канатом»-хребтом.
// Каждая ступень нанизана на спайн; цвет сегмента отражает статус
// (зелёный за решёнными, оранжевый у активной, тусклый за запертыми).
// Активная ступень — единственная тактильная карточка; остальные тихие.
export function Ladder({
  rungs,
  hint,
  showReveal,
  insertedKey,
  onSubmit,
}: LadderProps) {
  // Стабильный 1-based номер по ОРИГИНАЛЬНЫМ шагам (easier не нумеруем).
  let originalCounter = 0
  const numbered = rungs.map((r) => {
    if (r.kind === 'original') originalCounter += 1
    return { rung: r, num: originalCounter }
  })

  return (
    <ol className="flex flex-col">
      {numbered.map(({ rung, num }, i) => {
        const isLast = i === numbered.length - 1
        // Цвет хребта НИЖЕ этого узла = статус следующего перехода (токены AiPlus).
        const spineVar =
          rung.status === 'solved'
            ? 'var(--bg-success)'
            : rung.status === 'active'
              ? 'var(--bg-brand)'
              : 'var(--stroke-primary-disabled)'

        return (
          <li key={rung.key} className="relative flex gap-3 pb-3 last:pb-0">
            {/* Хребет-канат + узел-маркер */}
            <div className="relative flex w-6 shrink-0 flex-col items-center">
              <span
                aria-hidden
                className={`mt-3 size-3 rounded-full ${
                  rung.status === 'solved'
                    ? 'bg-bg-success'
                    : rung.status === 'active'
                      ? 'bg-bg-brand ring-4 ring-bg-brand/15'
                      : 'bg-stroke-primary-disabled'
                }`}
              />
              {!isLast && (
                <span
                  aria-hidden
                  className="mt-1 w-1 flex-1 rounded-full"
                  style={{ backgroundColor: spineVar }}
                />
              )}
            </div>

            {/* Тело ступени */}
            <div className="min-w-0 flex-1">
              {rung.status === 'active' && (
                <RungActive
                  rung={rung}
                  index={num}
                  hint={hint}
                  showReveal={showReveal}
                  justInserted={rung.key === insertedKey}
                  onSubmit={onSubmit}
                />
              )}
              {rung.status === 'solved' && <RungSolved rung={rung} index={num} />}
              {rung.status === 'locked' && <RungLocked rung={rung} index={num} />}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
