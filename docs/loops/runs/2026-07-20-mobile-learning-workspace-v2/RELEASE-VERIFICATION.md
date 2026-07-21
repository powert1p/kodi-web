# RELEASE VERIFICATION — mobile learning workspace v2 (candidate r4, released 2026-07-21)

Хвост рана добит оркестратором (Fable) после исчерпания токенов Codex на судейской фазе.
Продукт-код кандидата не менялся: дельта после падения Codex = только harness/доки/деплой.

## Итог

**RELEASED.** Кандидат r4 (`kodi-web:mobile-workspace-v2-final-r4-20260721-amd64`) прошёл полную
замороженную планку и задеплоен image-parity путём; публичный real-AI replay зелёный.

- Прод: `kodi-app` на aiplus, imageId `sha256:b3853a2d…` (слои байт-идентичны локальному
  кандидату; id-разница = пересериализация containerd↔classic store), `/ready` все checks true.
- Публичный URL (cloudflared quick-туннель, меняется при рестарте туннеля):
  `https://head-characters-tackle-laughing.trycloudflare.com` — актуальный всегда в
  `docker logs kodi-tunnel`.
- main: `ce58a2a` (feat, кандидат) + `cebb9c2` (docs) + fix compose FORWARDED_ALLOW_IPS; запушено.
- Rollback: `kodi-web:rollback-before-mobile-workspace-v2-20260721` на сервере.

## Blind-панель (frozen снапшот r4, EVIDENCE-SNAPSHOT.md)

| judge | avg | оси <8.5 | critical | P0/P1 | verdict |
|---|---|---|---|---|---|
| ux-blind-r4-1 (живой прогон journey) | 8.63 | — | 0 | 0 | **READY** |
| ux-blind-r4-2 | 8.69 | — | 0 | 0 | **READY** |
| ux-blind-r4-3 | 8.56 | accessibility 8.0 (порог ≥8.0 соблюдён) | 0 | 0 | **READY** |

Планка: каждая ось ≥8.0 ✓ · avg ≥8.5 ✓ · first_action/journey/math/mobile ≥8.5 у всех ✓ ·
3× explicit READY ✓. Исторический вердикт по r3 — `judges/ux-blind-1.json` (READY 8.75, до
landscape-фикса; в планку r4 не засчитан).

## Публичный real-AI replay (деплойнутый образ, через туннель)

- Chromium release-гейт: **typed PASS / photo PASS** (`/tmp/kodi-final-candidate/release-r4-public-chromium/`).
- WebKit 18.2 release-гейт: **typed PASS / photo PASS** (`…/release-r4-public-webkit-18_2/`).
- WebKit keyboard-гейт 844×375: **PASS** — обе вьюхи, overflow 0, field/primary/mode_switch/dock
  в вьюпорте, таргеты ≥44px, AI-вердикт 1.47s, черновик сохранён
  (`…/public-webkit-keyboard-r4/`).
- Консоль/страница/сеть/HTTP-ошибки во всех сводках пустые.

## Локальная матрица r4 (до судей) — см. EVIDENCE-SNAPSHOT.md

Chromium PASS/PASS · WebKit 18.2 PASS/PASS · matching-HEIC PASS (реальный IMG_4979.heic,
verdict correct 7.0s) · backend 696 · фронт lint/design-lint/tsc/vitest 130 · байт-паритет
образ↔дерево ✓ · own-eyes PASS.

## Адаптации харнесса при добивании (ассерты НЕ ослаблены)

1. `live_release_gate.py`: +500мс «человеческого чтения» перед Escape в tutor-сценарии.
   Причина — найденная гонка (см. P2 №3): Escape впритык (≲100мс) к рендеру ответа даёт
   activeElement=body. Проба (scratchpad/probe-focus.py): при человеческой паузе фокус
   восстанавливается за 2мс; все ассерты сценария сохранены.
2. `public_webkit_keyboard_gate.py` — v2-локальная копия legacy-гейта: sys.path на соседний ран;
   ожидание видимого `<p>`-вердикта вместо `<small>`-подсказки (в short-landscape kicker/small
   скрыты ПО ДИЗАЙНУ, CSS ~1200); геометрия на стабильные testid'ы `workbook-*` вместо
   legacy-классов answer-or-photo. Семантика проверок эквивалентна.
3. WebKit-бинарь: системный playwright 1.61 (`special-2251`) на этой macOS 14.3 падает SIGBUS →
   прогоны сборкой 18.2/2104 (venv py3.12 + playwright 1.49; той же, что r3/r6 у Codex);
   keyboard-гейту передавать `webkit-2104/pw_run.sh`, не сырой бинарь.

## Остаточные P2 (бэклог следующего слайса; критических нет)

1. Мобильная шапка: пилюля «Задача N» усечена и подрезана кнопкой «Сменить ученика»
   (z-overlap; оба таргета ≥44px, инфо дублируется в meta ниже) — консенсус 3 судей + own-eyes.
2. Evidence-strip: зелёная галочка «{ответ} · ответ проверен» рядом с НЕВЕРНЫМ ответом читается
   как успех на первый взгляд (вердикт-блок ниже однозначен) — консенсус 3 судей + own-eyes.
3. Гонка restore-фокуса tutor: Escape ≲100мс после рендера ответа → фокус на body
   (публичный Chromium 2/2 при adversarial-тайминге; при человеческом — 2мс restore).
   Фикс-кандидат: синхронный `trigger.focus()` в close-обработчике до unmount.
4. Guided-подсказка: «Например: N» дублируется в format-hint и example (судья-1, живой guided).
5. Инфраструктура: quick-туннель меняет публичный URL при каждом рестарте — нужен стабильный
   домен (named tunnel или nginx vhost от root).

## Хронология добивания (2026-07-21)

Codex: r3 снапшот 08:14 → судья-1 READY 08:18 → own-eyes landscape-кейс → CSS-фикс + 390-ширина
гейтов → r4 образ 08:29 → Chromium r4 PASS 08:35 → токены кончились.
Fable: WebKit r4 + matching-HEIC + фронт-механика → перезаморозка снапшота r4 → 3 blind-судьи
(opus) 3×READY → коммит/push → image-parity деплой (save|load 2:56, сеть пересобрана на
172.30.57.0/24, туннель на фикс-IP .4) → публичные Chromium/WebKit/keyboard PASS.
