// Внутренний код микро-навыка (INT_ADD_SUB, misinterpreted_operator) — НЕ подпись
// для UI (canon §2 п.2: запрет на snake_case/код в интерфейсе). Часть шагов
// приходит с читаемым русским label («Процент от числа»), часть — с сырым кодом
// декомпозиции (любой регистр). Различаем эвристикой: label всегда кириллица,
// код — чистая ASCII-латиница/цифры/подчёркивания (в любом регистре).
export function isRawSkillCode(s: string): boolean {
  return /^[a-zA-Z0-9_]+$/.test(s)
}

/** Читаемый label шага, если он есть; иначе null (вызывающая сторона подставит «Шаг N»). */
export function skillLabel(microSkill: string): string | null {
  return isRawSkillCode(microSkill) ? null : microSkill
}
