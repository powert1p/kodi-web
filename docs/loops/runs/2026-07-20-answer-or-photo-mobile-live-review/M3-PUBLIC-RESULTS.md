# M3 public results — exact answer-or-photo candidate

Дата финального прогона: 2026-07-20 (Asia/Almaty).

Public origin: `https://awesome-seas-gba-expanded.trycloudflare.com/app/`.

Итог: **PASS**. Печатный ответ и фото работают как два равноправных способа
закончить задачу. Правильный печатный ответ сразу открывает следующий шаг и не
требует фото. На compact mobile задача, input, feedback и действия остаются в
одном рабочем экране.

## Deployment and rollback receipt

Cutover заменил только `kodi-app`. PostgreSQL, его bind-mount, папка
`error_photos` и существующий Cloudflare tunnel не пересоздавались.

| Object | Exact current value |
|---|---|
| Candidate tag | `kodi-web:answer-photo-m4-feedback-final-20260720-amd64` |
| Build manifest fingerprint | `sha256:651890ba3a9047711fa0860a9cf0164db7beb976cef6161e220c192f8a6e3328` |
| Runtime image config | `sha256:539477d28656a22e603f8e96257d759cb6963b59f9748f3f1044d2ae243923d6` |
| App container | `14342d2aa5e2ace26629b8df8edbddb53921ae008bc30a184e70531c949ba099` |
| PostgreSQL container | `37a6c63115012e42dc1a6ab73df0f2f9454e9942ad304b3db02f90451a497356` |
| Tunnel container | `d1049810fb9110c5953d4e661b60e996a85aed60aed7e263870f096e053ea3d4` |

Rollback закреплён отдельно:

- `kodi-web:rollback-before-feedback-final-20260720` →
  `sha256:2840b5a215303336e6ff8bf884dd248775ab5acd95868a4b5a17b4c74b056bb3`.

Exact public assets совпали с файлами внутри candidate image:

- `JourneyPage-DK2o8Kkj.js` →
  `3a5e6443a3900857c3f373e2a1591aff289a5fab0b67b6a1b3b72ad47c6a674f`;
- `JourneyPage-Ix6dmPTC.css` →
  `b38ffa597b62cde7469bbc7654ed8919aa65fbd1b9b8fa5628c5e3ccf23ffb07`.

После всех public CJM:

- `kodi-app`: running, healthy, restart count `0`;
- `kodi-postgres`: running, healthy, restart count `0`;
- `kodi-tunnel`: running, restart count `0`;
- `/ready`: `database=true`, `pwa=true`, `ai_provider=true`;
- PostgreSQL bind fingerprint остался `pgdata=2051:411422588:4096`;
- перед финальным photo-CJM было `66` файлов, после двух ожидаемых upload — `68`;
- в production-логах за финальный прогон `0` строк с traceback, exception,
  critical или HTTP 5xx.

Во время container replacement был один краткий внешний HTTP 502 до перехода
нового app-container в healthy. После cutover public origin стабильно отвечает,
restart count остался `0`.

## Public typed-answer CJM

Fresh synthetic learner прошёл регистрацию, профиль, диагностику и открыл
первую полноценную задачу. Оба ответа проверены настоящим Gemini, не локальным
арифметическим скриптом.

| Scenario | Public result |
|---|---|
| Real Gemini incorrect | ответ `0`; pending виден через `2.3 ms`; HTTP 200 за `1.974 s`; та же задача, feedback виден в action dock, ответ сохранён, фото и помощь доступны |
| Real Gemini correct | ответ `15`; pending виден через `2.1 ms`; HTTP 200 за `1.100 s`; переход `independent_task → transfer_task`; новый заголовок сфокусирован; `photo_required=false` |
| Потеря HTTP-ответа + reload | сервер показал `typed_processing`, UI продолжил polling, после завершения восстановил verdict и введённый `0` |
| Typed/photo race | фото получило безопасный HTTP 409 с authoritative state; правильный typed-result сохранился и открыл `transfer_task` |
| AI unavailable / HTTP 429 / offline | draft сохранён, показан понятный retry, повтор использует тот же `client_attempt_id` |
| Stale revision | UI принял authoritative task, сообщил о смене задачи и разрешил явно вернуть draft `777` |

Durable evidence:

- `/tmp/kodi-answer-photo-public-final-pending-typed/public-typed-cjm-summary.json`
  — финальный `PASS` exact candidate;
- `/tmp/kodi-answer-photo-typed-processing-m3/summary.json` — disconnect,
  reload и race `PASS`;
- `/tmp/kodi-answer-photo-public-recheck/summary.json` — provider/offline/stale
  recovery `PASS`;
- `/tmp/kodi-answer-photo-public-final-pending-typed/typed-incorrect-844x375.png`;
- `/tmp/kodi-answer-photo-typed-processing-m3/typed-processing-before-reload.png`;
- `/tmp/kodi-answer-photo-typed-processing-m3/typed-correct-after-photo-race.png`.

У финального typed-CJM пустые `console_errors`, `page_errors`,
`request_failures` и `http_errors`.

## Public AI tutor and photo CJM

Новый ученик прошёл registration/profile/diagnostic через публичный UI. После
consent были проверены AI-помощник и два реальных vision-запроса.

| Scenario | Public result |
|---|---|
| AI tutor | HTTP 200 за `1.114 s`; дал один следующий вопрос без раскрытия ответа |
| Real `IMG_4979.heic` | `image/heic`, 1,249,354 bytes; HEIC конвертирован в JPEG; Gemini за `21.468 s` контекстно определил `wrong_photo`, сохранив текущую задачу |
| Correct JPEG | `image/jpeg`, 224,149 bytes; Gemini за `5.039 s` вернул `verdict=correct` и `photo_feedback` |

Photo evidence:

- `/tmp/kodi-answer-photo-public-final-feedback-photo/public-photo-cjm-summary.json`
  — `PASS`;
- `/tmp/kodi-answer-photo-public-final-feedback-photo/real-heic.png`;
- `/tmp/kodi-answer-photo-public-final-feedback-photo/known-correct-jpeg.png`.

У photo-CJM пустые `console_errors`, `page_errors`, `request_failures` и
`http_errors`. Production-логи подтверждают tutor, оба Gemini vision-вызова и
оба `POST /api/journey/photo` как HTTP 200.

## Mobile and desktop live review

Typed flow проверен на `375×844`, `844×375`, `932×430`, `1280×900`, а также
в реальном mobile WebKit с открытой системной клавиатурой. Photo task/typed
switch и photo feedback дополнительно проверены на `375×844`, `844×375` и
`932×430`.

Финальная compact mobile геометрия:

- `844×375`, typed incorrect: input `y=317..367`, primary
  `y=321.72..365.72`, photo switch `y=323..367`;
- `844×375`, WebKit + OS keyboard: input `y=317..367`, primary
  `y=321.72..365.72`, photo switch `y=323..367`, feedback после real AI
  verdict `y=119.95..254.13`, `visualViewport=844×375`;
- `844×375`, photo task: primary и answer switch `y=320.53..367`;
- `375×844`, next task: primary `y=732.81..780.81`, mode switch
  `y=787.20..831.20`;
- `375×844`, photo feedback: next-task action `y=783.20..831.20`;
- `932×430`, photo feedback: next-task action `y=378..422`.

Во всех этих состояниях `horizontal_overflow=0`; каждый указанный control
полностью находится внутри viewport. Компактный viewport-anchored dock не
перекрывает задачу, input или feedback и не заставляет искать действие на другой
странице.

Representative final renders:

- `/tmp/kodi-answer-photo-public-final-feedback-photo/task-375x844.png`;
- `/tmp/kodi-answer-photo-public-final-feedback-photo/task-844x375.png`;
- `/tmp/kodi-answer-photo-public-final-pending-typed/typed-incorrect-844x375.png`;
- `/tmp/kodi-answer-photo-public-final-feedback-photo/feedback-932x430.png`;
- `/tmp/kodi-answer-photo-public-final-pending-typed/next-task-375x844.png`;
- `evidence-public-webkit-keyboard-r6/public-webkit-os-keyboard-input.png`;
- `evidence-public-webkit-keyboard-r6/public-webkit-os-keyboard-feedback.png`.

Реальные кадры просмотрены вручную: portrait, compact landscape, typed
incorrect feedback, unrelated HEIC, correct photo и WebKit с открытой OS
keyboard не имеют P0/P1 дефектов.

Release-device gate закрыт публичным mobile WebKit-прогоном под Playwright:
iPhone Safari 17.5 user agent, touch/mobile context и viewport `844×375`.
Свежий ученик дошёл до полноценной задачи, ввёл `0`, получил настоящий AI
verdict `incorrect` за `1.376 s`, сохранил ответ и фокус в `short-answer`.
До и после feedback поле, feedback и все три действия полностью видимы при
открытой macOS Accessibility Keyboard; `horizontal_overflow=0`, console,
page, request и HTTP errors пусты. Системная клавиатура после capture возвращена
в исходное выключенное состояние.

Durable WebKit evidence:

- `evidence-public-webkit-keyboard-r6/public-webkit-keyboard-summary.json` —
  `PASS`, DOM/visualViewport/network/focus metrics;
- `evidence-public-webkit-keyboard-r6/public-webkit-os-keyboard-input.png` —
  SHA-256 `a24a880def2fa37250cf45eb67b701173e34f7bfc00f1c4c7e37dc23b83c0bd2`;
- `evidence-public-webkit-keyboard-r6/public-webkit-os-keyboard-feedback.png` —
  SHA-256 `ece1406e6aab562c75cf2b64024236d51ea53dbfd9cc5518664719aa8b79b59d`;
- `public_webkit_keyboard_gate.py` — воспроизводимый public gate; использован
  официальный isolated WebKit build `2104`, потому что локальный current
  browser bundle на этой macOS завершается до запуска с `Bus error: 10`.

## Mechanical gates for the exact deployed source

- full backend with PostgreSQL: `710 passed, 28 warnings in 71.32s`;
- full webapp: `20` files / `128` tests passed;
- `npm run build`: passed;
- `npm run lint:design`: clean, `122` files checked;
- Oxlint: exit `0`, только три pre-existing warning в
  `AuthContext`, `ConsentCard`, `useRoutePath`;
- оба public CJM: `PASS`; `git diff --check` и Python compile gates: clean.
