# RUBRIC design — оверрайд kodi-web (zero-based redesign)

Source method = `~/Documents/design-lab/AUDIT-RUBRIC.md`: полностраничные скриншоты + чтение
кода, judge-панель 3 судьи, 8 осей 0–10 с якорями, порог «СУПЕР», JSON-вердикт и «Докрутка
флоу». Для каждого production run применимая версия **копируется в локальный `RUBRIC.md` и
хешируется**; judges не зависят от mutable внешнего файла. Если источник используется напрямую,
его SHA-256 также входит в contract snapshot. Ниже — адаптация к мобильному приложению kodi-web.

Процесс и terminal semantics заданы в `DESIGN-FLOW.md`: known-shape UI не раздувается до
benchmark, а rejected/clean-slate design проходит generator-loop. Creative bar железная:
budget или plateau ниже неё фиксируются как `NOT_READY/UNCERTAIN`, но не «готово».
Production READY требует три явных judge verdict `READY`; отсутствие третьего = `BLOCKED`.

## Оверрайд для webapp/ (React PWA тренажёра)

- **Бриф** = product truth из `docs/VISION.md` + `BRIEF.md` конкретного run'а. Старые
  `DESIGN-V*.md`, `webapp/DESIGN_SYSTEM.md`, существующие компоненты и текущие скриншоты —
  только evidence о поведении и anti-reference, но НЕ визуальный канон для clean-slate раунда.
- Ось `brief_fit` читает задачу экрана и аудиторию 10–13 лет: интерфейс не должен быть ни
  взрослым luxury-лендингом, ни kiddie-игрой; серьёзность подготовки сочетается с ясностью,
  энергией и психологически безопасным feedback.
- **Скриншоты** = **375×844 и 1280×900**. В concept-round обязательны hub, drill и srez;
  в React-раунде — login, hub, srez, drill, closure и analytics. Судья смотрит весь набор,
  а не один удачный hero.
- **«Визуальный панч»** для приложения = первый вьюпорт каждого ключевого экрана имеет
  решительную art direction, атмосферу, custom visual field/asset и один ясный фокус.
  «Аккуратные карточки на светлом фоне» и «mobile-card по центру desktop» = 5–7 (провал).
- **Craft-оси авто-потолки:** внутренние идентификаторы (snake_case) в UI · красный для ошибок · учебный текст <18px · тач <44px · второй primary-CTA на экране · фейковые данные в декоре (нечестные шкалы/числа) → ось craft ≤4 автоматом.
- **Signature** должен быть ОДИН, сквозной через hub/drill/srez, командовать первым viewport,
  работать на mobile в полноценной форме и использовать только честные данные. Generic progress
  bar, numbered cards, sidebar rail и mascot сами по себе signature не считаются.
- **Clean-slate gate:** до React сравниваются минимум три концепта с разными spatial model,
  typography, atmosphere и signature. Вариант, меняющий только tokens/radius/font поверх старого
  DOM, получает `composition ≤5` и `signature ≤4`.
- **Asset gate:** у победителя есть хотя бы один собственный visual asset или равноценная
  code-native композиция, встроенная в структуру, а не помещённая «картинкой в карточку».
- **Рендер:** R1 (статичные HTML-концепты) — `file://` через Playwright-скрипт run'а;
  R2+ (React) — vite localhost:5173 или production preview, console чистая, без
  горизонтального скролла. Keyboard focus и reduced-motion проверяются отдельно.
- **Детектор** = команды, frozen в contract конкретного run'а; минимум `npm run lint:design`.
  Screenshot/URL detector добавляется только если доступен и smoke-проверен до maker round;
  отсутствие или `NOT_RUN` обязательного detector не считается PASS.
- Дельты и починки флоу → `docs/loops/FLOW-CHANGELOG.md` (kodi-web), кросс-переносимые уроки дизайн-флоу → `~/Documents/design-lab/FLOW-CHANGELOG.md`.
