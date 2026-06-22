# kodi-web Tests

> Состояние на 2026-06-22: тестов практически **0** (нет `backend/tests/`, pytest не в requirements; frontend — 1 smoke не компилится из-за `dart:html`). Это главный P2-долг (AUDIT TEST-0).

## Backend — pytest + pytest-asyncio
- Команда: `.venv/bin/pytest backend/tests/ -x -q` (после ввода).
- Начинать с **pure-функций** (легко и ценно): `core/grading.py:check_answer` (table-driven, примеры в docstring готовы), `core/bkt.py:bkt_update`/`is_mastered` (golden values), `core/diagnostic.py:_reconstruct_levels`/`_compute_additive_mastery`.
- Integration на эндпоинты — против РЕАЛЬНОГО Postgres (не мокать БД). Мокать только внешние границы (Anthropic API).
- Каждая фича: happy path + error (401/403/404) + edge (null/0/empty).
- Два живых бага (exam/start 500, невалидный Claude id) были бы пойманы одним integration-тестом каждый — приоритет.

## Frontend — bloc_test
- После фикса `dart:html` (FE-1): `bloc_test` для AuthBloc (persist/restore, error-пути), Practice/Diagnostic/Exam blocs.
- Unit на `MathText._convertToLatex` (нетривиальный regex) и `fromJson` моделей. Работают на VM, без браузера.

## Правило
- НЕ удалять/менять существующие тесты ради зелёного — чинить код.
- TDD для новых фич: тест (падает) → имплементация → рефактор.

## Гейты до «done»
- `.venv/bin/pytest backend/tests/ -x -q` зелёный + `flutter analyze` 0 errors + `flutter build web --release` проходит.
