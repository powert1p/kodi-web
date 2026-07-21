# Live reproduction — answer or photo / mobile

Дата: 2026-07-20  
Публичный origin: `https://awesome-seas-gba-expanded.trycloudflare.com`  
Ученик: новый disposable learner, созданный runner; аккаунт владельца не использовался.

## Что запущено

```text
KODI_TEST_PIN=<synthetic> .venv/bin/python live_cjm_gate.py \
  --base-url https://awesome-seas-gba-expanded.trycloudflare.com \
  --output-dir /tmp/kodi-live-baseline-20260720 \
  --fixture-dir fixtures
```

Runner прошёл регистрацию, profile, diagnostic, personal route, live tutor, typed submit,
photo recovery, guided flow, transfer и topic result. Он использовал реальный публичный API и
реального AI provider.

## Наблюдаемый submit timeline

| Сигнал | Факт |
|---|---|
| Tap | Нажата `Проверить ответ` на mobile 375×844 |
| Request | `POST /api/journey/answer` |
| HTTP | `200` |
| AI verdict | `correct` |
| Время до response | `1254 ms` |
| Смена problem | Нет: `sameProblem=true` |
| Mastery | Нет: `countsForMastery=false` |
| UI после success | `Короткий ответ сходится` → обязательное фото той же задачи |
| Console/page/request/API errors | `[] / [] / [] / []` |

Итог: transport и AI работали. Ошибка — продуктовый/backend contract: `correct` намеренно
оставался formative feedback. Поэтому пользователь видел долгую проверку без прогресса, а затем
получал требование фото, которое обесценивало typed submit.

## Наблюдаемый mobile defect

До submit на 375×844 условие и primary action видны. После typed response поле ввода удаляется,
но текущая task не меняется и scroll offset, созданный фокусом нижнего fixed dock, сохраняется.
В результате условие целиком оказывается выше viewport: сверху остаётся большое пустое поле,
видны только feedback и высокий fixed dock. Это нарушает stable task anchor и делает непонятным,
что произошло.

Отдельный live probe подтвердил второй P0 на 844×375. Breakpoint mobile-layout заканчивается
на 840 px, поэтому viewport шириной 844 px ошибочно получает desktop three-column grid. Primary
action имеет правую координату 966 px и обрезается на 122 px; `overflow-x: clip` скрывает дефект
вместо перекомпоновки. На 375×844 реальный typed dock имеет высоту 226 px при зарезервированных
184 px. Headless browser не показывает системную soft keyboard, поэтому keyboard-resize остаётся
обязательным real-device gate.

Baseline evidence:

- `/tmp/kodi-live-baseline-20260720/photo-first-task-mobile-375x844.png`
- `/tmp/kodi-live-baseline-20260720/live-ai-typed-feedback-mobile-375x844.png`
- `/tmp/kodi-live-baseline-20260720/live-cjm-summary.json`
- `/tmp/kodi-live-audit-20260720/workspace-844x375-viewport.png`
- `/tmp/kodi-live-audit-20260720/typed-375-max-scroll-focus.png`
- `/tmp/kodi-live-audit-20260720/workspace-1280x900-viewport.png`

## Server evidence

За окно live review контейнер `kodi-app` записал успешные
`POST /api/journey/answer HTTP/1.1 200 OK`; `409/5xx` для этого submit не было. Readiness:
database, PWA и AI provider — healthy.

## Вывод для implementation

1. `correct` должен атомарно завершить текущую task и открыть следующую без фото.
2. UI обязан показать локальный pending сразу, затем success и новую task, вернуть scroll/focus к
   task anchor.
3. Stale/offline/provider failure должен оставлять draft и давать явный retry/reload.
4. Typed mode и mobile landscape не должны использовать высокий fixed dock, который конкурирует
   с visual viewport и клавиатурой.
5. Responsive gate проверяет rect каждого интерактивного элемента, а не только `scrollWidth`:
   `left >= 0`, `right <= innerWidth`, primary и switch видимы и доступны для tap.
