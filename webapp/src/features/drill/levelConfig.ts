// Уровень разбора выводится из mastery узла (state ученика).
// Чем выше владение — тем ближе к «почти получилось».
// Уровень задаёт настроение маскота и рамочную копию (growth-mindset).

import type { WrongTask } from '../../lib/types'

export type DrillLevel = 1 | 2 | 3

/** Выводит уровень разбора из mastery: низкое → 1, среднее → 2, высокое → 3. */
export function levelFromTask(task: WrongTask): DrillLevel {
  if (task.mastery >= 0.6) return 3
  if (task.mastery >= 0.4) return 2
  return 1
}

interface LevelMeta {
  /** Эйнбров над заголовком интро. */
  eyebrow: string
  /** Короткая рамочная строка (голос маскота). */
  line: string
  /** Настроение маскота для интро. */
  mood: 'hi' | 'thinking'
}

export const LEVEL_META: Record<DrillLevel, LevelMeta> = {
  1: {
    eyebrow: 'Уровень 1 · с нуля',
    line: 'Разберём тему вместе — по одному маленькому шагу. Спешить некуда.',
    mood: 'hi',
  },
  2: {
    eyebrow: 'Уровень 2 · напоминание',
    line: 'Метод ты уже знаешь — давай вспомним, как решать. Подскажу, если что.',
    mood: 'thinking',
  },
  3: {
    eyebrow: 'Уровень 3 · почти получилось',
    line: 'Ты был совсем близко. Давай найдём один шаг, где сбилось — и закроем.',
    mood: 'thinking',
  },
}
