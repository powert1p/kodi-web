# Immutable candidate evidence — mobile learning workspace v2 (candidate r4)

Snapshot frozen on 2026-07-21 (r4) after production mechanics, exact-browser render and real-AI
journeys. Judges must score this snapshot and must not change files.

> История: r3 был заморожен утром 2026-07-21 и получил READY от ux-blind-1 (`judges/ux-blind-1.json`,
> оценивал r3-артефакты). После заморозки maker нашёл own-eyes крайний случай short-landscape
> (после переключения в «Ввести ответ» primary CTA уходил ниже первого экрана) → CSS-фикс
> `LearningWorkspace.css` + расширение release-гейта шириной 390 → кандидат r4. Панель судей
> запускается заново на r4; вердикт по r3 — исторический, в планку r4 не засчитывается.
> Дельта r3→r4 (единственная): `webapp/src/features/journey/LearningWorkspace.css` +
> harness (`live_release_gate.py`, `public_photo_cjm_gate.py` — добавлена 390-ширина).

## Candidate identity

- Docker tag: `kodi-web:mobile-workspace-v2-final-r4-20260721-amd64`
- Image id: `sha256:0698c1aa7eb6361b350212c278c05b29d82334cb13faf9103396e14cd7295d1d`
- Platform and size: `linux/amd64`, `374854078` bytes.
- Local candidate: `http://127.0.0.1:8302`; `/ready` = `{database:true, pwa:true, ai_provider:true}`.
- Байт-паритет проверен оркестратором: 7 backend-файлов + built `JourneyPage-Co3UBTLK.css` /
  `JourneyPage-uXIvlu9v.js` / `index.html` внутри образа = рабочее дерево byte-for-byte;
  полный список хэшей — `CANDIDATE-SHA256SUMS` (перегенерирован под r4).

## Mechanical gates

- Backend: `696 passed` против изолированного реального PostgreSQL (заморозка r3; backend-файлы
  в r4 байт-идентичны r3 — см. CANDIDATE-SHA256SUMS, дельта только CSS/harness).
- Frontend (перегнано на r4-дереве оркестратором): ESLint clean · design-lint clean ·
  `tsc -b` clean · vitest все зелёные (см. RELEASE-VERIFICATION).
- Frontend build: release Vite/PWA build = ассеты внутри r4-образа (паритет подтверждён хэшами).
- `git diff --check`: clean.

## Chromium real-AI journey (r4, 2026-07-21 08:35)

- Combined verdict: typed `PASS`, photo `PASS` (`release-r4-final-chromium/release-summary.json`).
- Geometry: `typed-incorrect-390x844`, `typed-incorrect-844x375`, `next-task-375x844`,
  `next-task-390x844`, `next-task-1280x900` + 9 photo-стейтов (375/390/844×375/932×430/1280).
- Horizontal overflow 0 везде; console/page/request/http errors пустые; контролы ≥44px.
- Incorrect typed: AI-вердикт, задача и draft сохранены. Correct typed `15` → transfer без фото.
- Tutor: контекстный ответ, Escape → фокус и scroll восстановлены.
- Real HEIC чужой задачи → same-surface recovery; known-correct JPEG → AI verdict correct.
- Артефакты: `/tmp/kodi-final-candidate/release-r4-final-chromium/`.

## WebKit real-AI journey (r4, 2026-07-21 15:0x)

- Browser: Playwright WebKit 18.2 (build v2104), тот же движок, что в r3-прогоне.
- Combined verdict: typed `PASS`, photo `PASS` (`release-r4-final-webkit-18_2/release-summary.json`).
- 5 typed + 9 photo геометрий; overflow 0; console/page/request/http errors пустые.
- Артефакты: `/tmp/kodi-final-candidate/release-r4-final-webkit-18_2/`.

## Exact reported HEIC on its matching task (r4)

- Input: `/Users/esetseitkamal/Downloads/IMG_4979.heic`, MIME `image/heic`, `1 249 354` bytes.
- Matching task: `Не вычисляя, определите, какая из дробей дальше от 1/2: 3/7 или 4/9?`
- AI: HTTP 200, `7.035s`, stage `photo_feedback`, verdict `correct`;
  сообщение «Решение верное. Теперь проверим перенос на новой задаче.»
- Артефакты: `/tmp/kodi-final-candidate/matching-heic-r4/`.

## Render artifacts for blind review

- `/tmp/kodi-final-candidate/release-r4-final-chromium/{typed,photo}/*.png` + summaries
- `/tmp/kodi-final-candidate/release-r4-final-webkit-18_2/{typed,photo}/*.png` + summaries
- `/tmp/kodi-final-candidate/matching-heic-r4/matching-heic.png`

## Own-eyes оркестратора (перед судьями)

PASS. Landscape-фикс подтверждён (844×375: CTA в первом экране, двухзонная композиция).
Два вопроса переданы судьям без предрешения: (1) мобильная шапка — пилюля статуса усечена под
кнопкой выхода; (2) микрокопия «✓ ответ проверен» рядом с неверным ответом — читаемость галочки.

## Frozen acceptance status before judges

- Open P0/P1: `0` (own-eyes + механика).
- Critical flags: `0` из выполненных гейтов.
- Деплой сознательно отложен: три fresh blind judges должны вернуть `READY` по ЭТОМУ снапшоту
  (r4); затем деплой ровно этого образа и публичный real-AI replay.
