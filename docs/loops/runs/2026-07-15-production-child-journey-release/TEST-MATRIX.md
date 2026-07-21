# Release test matrix

Статусы: `PENDING`, `PASS`, `FAIL`, `BLOCKED`. Реальный AI-тест помечается `LIVE`; monkeypatch/mock не засчитывается.

| ID | Journey / invariant | Level | Expected | Status |
|---|---|---|---|---|
| M-01 | Backend full suite with isolated PostgreSQL | integration | 0 skip / 0 fail | PASS — 508 passed, 22 warnings |
| M-02 | Frontend Vitest | unit/component | 0 fail | PASS — 91 passed in 16 files |
| M-03 | lint + design lint + TypeScript + Vite build | static/build | clean; only known warnings documented | PASS — build clean; 3 pre-existing lint warnings documented |
| M-04 | Flutter release build + Docker image | build | reproducible | PASS — `flutter analyze` clean; release image built from committed tree |
| J-01 | Register grade 7, consent not granted | API/browser | token + correct profile; no photo access | PASS — public API + mobile browser |
| J-02 | Wrong PIN then valid login | browser | actionable error then recovery | PASS — public mobile journey |
| J-03 | Fresh path → worked → guided → independent → transfer → result | browser 375/1280 | persisted completion, no console/API/overflow errors | PASS — public browser, 11 checkpoints |
| J-04 | Wrong answer, reload, aborted request, idempotent retry | browser/API | draft/support/state preserved, no double count | PASS — retry reused the same `client_attempt_id` |
| J-05 | Returning login | browser/API | exact completed state and result restored | PASS — fresh login verified on mobile and desktop |
| J-06 | Loading/error/empty/reduced-motion/focus/touch | browser/tests | accessible equivalent states | PASS — component contracts + public focus/touch/overflow checks |
| P-01 | Photo without consent | API/browser | 403 `consent_required`, zero provider/storage work | PASS — public API and browser |
| P-02 | Invalid MIME, empty/corrupt file, >8 MiB | API | safe 4xx, no capture persisted | PASS — integration suite + public corrupt fixture |
| P-03 | Synthetic handwritten expected step | LIVE Gemini | grounded `match` with confidence | PASS — `match`, confidence 1.0 |
| P-04 | Synthetic handwritten wrong step | LIVE Gemini | grounded `mismatch` or honest `unsure`; no answer leak | PASS — grounded `mismatch`, confidence 1.0 |
| P-05 | Rotation/low-resolution photo and provider failure | LIVE/API | no false certainty; retryable honest state | PASS — rotated match, low-res mismatch, retryable 503 |
| A-01 | Tutor first reply on active problem/step | LIVE Gemini | concrete method, ≤3 short sentences, exactly one question, no answer | PASS — public live provider |
| A-02 | Tutor follow-up and session reuse | LIVE Gemini/API | same session; history 2→4; contextual reply | PASS — public live provider |
| A-03 | Direct prompt to reveal answer/expected step | LIVE Gemini | refuses and asks next-step question | PASS — protected values absent |
| A-04 | LLM unavailable/rate limit | API/browser | honest 503/429; message preserved/retryable | PASS — backend gates + public browser retry |
| C-01 | Answer correctness | code review/API | determined by grading code, never LLM | PASS — server-side grading covered by suite and live journeys |
| C-02 | Lesson manifest + problem/decomposition identity | data/tests | canonical stable IDs, no answer leakage | PASS — covered by suite |
| C-03 | Completion/progress telemetry consistency | DB/API | one accepted attempt → one state transition; progress agrees | PASS — learning + closure idempotency verified live |
| S-01 | Server env/secrets | VPS | `.env` 600; JWT/Gemini set; no values logged | PASS — mode 600; readiness green; logs redacted/clean |
| S-02 | HTTPS and network exposure | VPS/external | HTTPS; app/DB raw ports not public | PASS — TLS verified; ports 8300/5435 bound to `127.0.0.1` |
| S-03 | Backup/rollback | VPS | DB backup + previous app artifact/tag + validated restore artifact | PASS — dump validated; rollback image and compose backup retained |
| S-04 | Production smoke and full journey | external browser/API | repeat J/P/A gates against deployed build | PASS — 29 public screenshots + API/Gemini canaries |

## Stop conditions

- Не деплоить новый build, пока M-01..M-04 или локальные J-gates красные.
- Не маркировать controlled pilot, пока любой `LIVE` AI gate, S-01 или S-02 красный.
- Не использовать реальные фото детей в release testing; только synthetic/non-personal fixtures.

## Release evidence — 2026-07-16

- Source commit: `baf555c` (`fix: make closure completion durable`).
- Deployed image: `sha256:e755c6ae60dbaaba044123d9fe72614b6284af45c95274286e45f2ea22af307d`.
- Public origin: `https://wearing-ministers-indexes-mono.trycloudflare.com`.
- Readiness: database, PWA and AI provider are all green; app restart count is zero.
- Runtime audit after the public journeys: 316 log lines, 0 traceback, 0 error/critical, 0 HTTP 5xx.
- Durable browser evidence: [`evidence-public-browser-baf555c`](./evidence-public-browser-baf555c/summary.json) and [`evidence-public-learning-baf555c`](./evidence-public-learning-baf555c/summary.json).
- Durable LIVE Gemini evidence: [`vision.json`](./evidence-public-api-baf555c/vision.json) and [`vision-robustness.json`](./evidence-public-api-baf555c/vision-robustness.json).
- Public closure canary: first submission recorded once; exact retry marked duplicate; conflicting payload returned 409; later wrong attempt reopened the queue; correct closure removed it.
- Backup: `/home/eset/kodi-web/backups/kodi-20260715T192837Z.dump`, 881034 bytes, mode 600.
- Rollback image: `kodi-web:rollback-before-baf555c-20260716T004906Z`; compose backup: `/home/eset/kodi-web/docker-compose.online.yml.pre-baf555c-20260716T004906Z`.

## Product boundary

Технически это проверенный controlled-pilot build: ребёнок может пройти один полноценный накопительный урок, получить помощь по фото/от AI, выполнить independent + transfer и вернуться к сохранённому результату. Это ещё не полный курс подготовки к НИШ: сейчас authored один конкретный урок (`mixtures-1`), поэтому рост экзаменационного результата нельзя честно обещать до расширения curriculum и продольного pre/post измерения.

## Next step

Следующий продуктовый инкремент — authored второй накопительный урок на том же skill graph и pre/post замер по его independent + transfer задачам. Старый поток «Сегодня — закрыть ошибки» не возвращать как главный маршрут: review остаётся вторичным recovery-инструментом внутри долгосрочного «Моего пути».
