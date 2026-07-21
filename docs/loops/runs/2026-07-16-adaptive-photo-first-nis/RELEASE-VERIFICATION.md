# Production release verification — adaptive photo-first NIS

Дата проверки: 2026-07-17 00:07 +05.

## Journey workspace envelope r17 — 2026-07-17 16:46 +05

- Production image: `kodi-web:workspace-envelope-r17-amd64`, `linux/amd64`, image config
  `sha256:199a4461efdcedadc2e91980df398c1116bf36bbe38042118c5c6e57156d4ba6`.
- Нормализованный fingerprint `Config + RootFS + platform` локально и на VPS совпал:
  `4ccec6cc4122014d7df6f69bba1c527ccab583a042bcf1e825bfeebc5c9e0a93`.
- Rollback image: `kodi-web:rollback-pre-workspace-r17-20260717T114643Z`.
- Image-only cutover завершён в `2026-07-17T11:46:44Z`; production DB, `.env`, persistent
  `error_photos` и работающий Cloudflare tunnel не заменялись и не перезапускались.
- Public URL: <https://observer-terrorists-reputation-chosen.trycloudflare.com>. `/ready`:
  database, PWA и AI provider — `true`; `kodi-app` healthy, restart count `0`.
- [Full production CJM](evidence/live-cjm-production-r17/live-cjm-summary.json) — `PASS`:
  две новые регистрации, разные персональные маршруты, exact
  resume diagnostic/guided, 19 screenshots на 375×844 и 1280×900, horizontal overflow `0`,
  `consoleErrors/pageErrors/requestErrors/apiErrors` пусты.
- CJM сделал 5 реальных Gemini-вызовов: безопасное восстановление плохого фото (`wrong_photo`,
  2748 ms), неверный первый шаг (`incorrect`, 2771 ms) и три правильных полных решения
  (3327/3072/3314 ms). Финальный mastery: `p=0.999`, correct `3/4`, accuracy `0.75`.
- Live harness проверил `workspace_version=1` и полный workspace envelope в 7/7 активных
  состояниях journey, включая отдельный poll во время `photo_processing`; во всех встреченных
  неактивных ответах отсутствовали все шесть ключей envelope.
- Production DB после CJM: `0` duplicate keys в `student_journeys`, `journey_attempts`,
  `practice_submissions`, `verification_submissions`, `learning_attempts`; `0` orphan journeys
  и attempts. После cutover в логах нет `ERROR/CRITICAL/Traceback/5xx`.
- Harness принимает любой безопасный AI recovery verdict (`unreadable`, `wrong_photo`,
  `unsure`) для заведомо непроверяемого фото и по-прежнему fail-closed требует recovery state.

## AI-owned photo grading patch r16 — 2026-07-17

- Production image: `kodi-web:photo-ai-grading-r16-amd64`, `linux/amd64`, image config
  `sha256:6cf5377e48debd33b062440d9ba3fade4a1a6f7dba82f0863e9b681eb185307a`.
- Rollback image: `kodi-web:rollback-pre-selection-grounding-r16`.
- Vision AI получает условие, полный canonical stage context, ожидаемые значения и правильный
  ответ; backend ограничен schema/range/step validation и не пересчитывает математику.
- Реальный `IMG_4979.heic`: исходная задача «дальше от 1/2» — `correct` 3/3; тот же снимок с
  контрольным вопросом «ближе к 1/2» — `incorrect`, `failed_step=3` 4/4. Во всех семи ответах
  Gemini явно распознал обводку `54/126` и галочку, поэтому verdict привязан к выбору ученика.
- Backend regression: `458 passed, 182 skipped`; targeted AI contract suite: `93 passed`;
  независимый review после acceptance delta — `APPROVE`.
- Public `/ready`: database, PWA и AI provider — `true`; `kodi-app` healthy, restart count `0`,
  после деплоя нет `ERROR/CRITICAL/Traceback/5xx`.

## Release identity

- Проверенный образ: `kodi-web:adaptive-photo-production-r13-amd64` (`linux/amd64`).
- OCI manifest: `sha256:4ef617f70f501aeb0d9b168b1d06e717b69776a715e2cc979c2f896b3530922c`.
- Исполняемый image config на VPS: `sha256:4e30a7b51db29c7cf24a3a7d02169a20f32411de308f658a820d16e4242582cc`.
- Нормализованный fingerprint `Config + RootFS + platform` локально и на VPS: `c892b17f580ceeeab68827577a14bd7f647768315e1b61d5728d920e7a87f78a`.
- Предыдущий production image сохранён как `kodi-web:rollback-pre-r12-20260716`.
- Деплой выполнен image-only; production DB и persistent `error_photos` не заменялись.

## Public production

- URL: <https://observer-terrorists-reputation-chosen.trycloudflare.com>
- `/ready`: database, PWA и AI provider — `true`.
- Quick Tunnel URL временный: при перезапуске `kodi-tunnel` Cloudflare выдаст новый адрес.

## Acceptance evidence

- [Production state matrix](evidence/state-matrix-production-r13/state-matrix-summary.json): `PASS`, 40 состояний, 80 screenshots, 375×844 и 1280×900, без неожиданных console/page/request/API errors.
- [Production live CJM](evidence/live-cjm-production-r13/live-cjm-summary.json): `PASS`, две новые регистрации, разные персональные маршруты, exact resume диагностики и guided-разбора, 19 screenshots.
- [Exact-image local state matrix](evidence/state-matrix-r13/state-matrix-summary.json): `PASS`, 80 screenshots.
- [Exact-image live CJM](evidence/live-cjm-amd64-r13/live-cjm-summary.json): `PASS` с реальным Gemini.
- Photo-first Gemini: `unreadable`, ошибка на первом неверном шаге и три корректных полных решения подтверждены на production.
- Guided-разбор не повышает mastery; навык подтверждается только после `3/4` самостоятельных решений (`p=0.999`, accuracy `0.75`).
- Production DB: `0` duplicate keys в `practice_submissions`, `journey_attempts`, `verification_submissions`, `learning_attempts`; `0` orphan journeys.
- После production CJM: `0` server `ERROR/CRITICAL/Traceback/5xx`, `kodi-app` restart count `0`.

## Mechanical and independent gates

- Backend: `640 passed`.
- React PWA: `113 passed`; typecheck и production build — clean.
- Flutter: `flutter analyze`, Chrome tests и release web build — pass.
- Blind release review: `READY`, без P0/P1/P2 после acceptance delta.
- Visual benchmark: `READY`, `8.95/10`, `wow=true`, critical flags `0`.

Неблокирующий шум harness: Playwright на закрытии отдельных browser contexts печатает `Target closed`; оба CJM завершились с exit code `0`, а `consoleErrors`, `pageErrors`, `requestErrors` и `apiErrors` в итоговых JSON пусты.
