# FEAT-XXX: [Название]

## Проблема
[Зачем это нужно. Что ломается / отсутствует / мешает]

## Решение
[Высокоуровневый подход]

## Файлы
| Файл | Действие | Что |
|------|----------|-----|
| path/to/file | CREATE/MODIFY | Краткое описание |

## Acceptance Criteria
- [ ] [Конкретный, тестируемый критерий]
- [ ] `.venv/bin/pytest backend/tests/ -x -q` проходит
- [ ] `flutter analyze` 0 errors, `flutter build web --release` проходит
- [ ] UI-изменения проверены через Playwright (если фронт)

## Edge Cases
- [Что если X = null/пусто/0?]
- [Что при ошибке?]

## Security
- [SQL injection? Auth (JWT)? Секреты из env?]

## Out of Scope
- [Что эта фича НЕ делает]
