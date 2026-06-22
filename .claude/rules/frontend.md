# kodi-web Frontend — Flutter Web

## Стек (НЕ React — это Flutter/Dart)
- Flutter Web (стабильный канал, проверено на 3.41.2 / Dart 3.11.0), Material 3, **светлая тема**.
- State management: **BLoC** (один bloc на фичу: Auth/Dashboard/Practice/Diagnostic/Exam), Equatable events/states.
- Монорепо: `apps/kodi_web` (приложение) + `packages/kodi_core` (модели + API-клиент, path-dependency).
- LaTeX — `flutter_math_fork` через единый виджет `MathText` (auto-конверт текста в LaTeX).

## Архитектура
- Один bloc = одна фича. Виджеты тонкие, логика в bloc. DI через провайдеры.
- API — ТОЛЬКО через `packages/kodi_core/lib/api/nis_api.dart` (`NisApiClient`). Не создавать прямые http-вызовы в фичах.
- `NisApiClient` различает `NetworkException` vs `ApiException` — каждый bloc ловит оба + generic fallback с локализованным ключом.
- Модели — `kodi_core/lib/models/` с null-safe `fromJson`. Типы сверять с backend Pydantic-схемами.

## Конфиг и API
- `API_BASE_URL` — **compile-time** (`String.fromEnvironment`), задаётся `--dart-define` при билде. Dockerfile билдит пустым → same-origin relative `/api/...`.
- ⚠️ При смене origin меняется ребилдом образа (нет runtime-конфига). Для VPS — держать same-origin (nginx проксирует `/api/` на backend под тем же hostname). См. AUDIT FE-3.
- Никаких хардкод-секретов/URL (кроме `localhost:8000` dev-default, перекрытого dart-define).

## Локализация
- ru/kz через `.arb` (`app_ru.arb` / `app_kk.arb`), 200/200 ключей. Новый текст — в ОБА файла, не хардкодить строки.

## UI / дизайн
- **Перед UI-работой читать `DESIGN_SYSTEM.md`** — токены (цвета/радиусы/шрифты) централизованы в `lib/app/colors.dart` + `theme.dart`.
- ⚠️ Сейчас шрифт — **Roboto** (дефолт Flutter), нарушает правило «NEVER Inter/Arial/Roboto». При UI-полировке — заменить на выразительный humanist-sans (Nunito/Lexend/Onest). Backlog.
- Каждый компонент: loading / error / empty / success состояния (уже есть базово).
- ⚠️ `dart:html` в `login_page.dart` ломает `flutter test` и WASM — мигрировать на `package:web`+`dart:js_interop` (AUDIT FE-1).

## Верификация после изменений
- `flutter analyze` (0 errors), `flutter build web --release` (должен пройти).
- Визуальная проверка через Playwright MCP (navigate → snapshot → screenshot → console без ошибок). НЕ говорить «done» без визуальной проверки.
