# Production onboarding нового ученика — результат

## Release candidate

- Product commit: `a6265c64e8afd3eb9a540d1d1e35501340fad36a`.
- Tested tree: `79f8b0147a6a641c967676a8faf07fb29950f27e`.
- Проверенный публичный URL: <https://wearing-ministers-indexes-mono.trycloudflare.com/app/>.
- Production container: `kodi-app`, `healthy`, restart count `0`.
- Публичный CJM после deploy: `PASS` на `375×844 touch` и `1280×900`.

Это уже не dashboard-MVP: новый ученик регистрируется и без промежуточного выбора попадает в
серверный урок `mixtures-1`. Первый meaningful answer сохраняется, а reload и повторный login
возвращают в тот же server session и состояние `2/6`.

## Frozen critical gates

| Gate | Результат | Evidence |
|---|---|---|
| `/`, `/app` → React PWA; deep links; missing asset 404 | PASS | [`evidence/public-browser-a6265c6/summary.json`](evidence/public-browser-a6265c6/summary.json), `route_matrix` |
| Новый номер регистрируется через реальный UI | PASS | тот же artifact, `registration_to_activity` |
| Submit сразу открывает математику | PASS, `2186 ms` | `path_response_lesson_id=mixtures-1`, `browser_destination=/app/lesson/mixtures-1` |
| Нет dashboard/diagnostic/photo/chat до урока | PASS | browser checkpoints `01` → `02` → `03-first-math-direct` |
| Фото-согласие не входит в детскую регистрацию | PASS | `photo_consent=null`, checkbox отсутствует |
| Lesson id приходит из `/api/learning/path/current` | PASS | response перехвачен до route transition и сопоставлен с URL |
| Ошибка path не уничтожает аккаунт | PASS | `path_failure_recovery`: injected `503`, JWT и `/auth/me` сохранены, затем path `200` |
| Reload/relogin не создают duplicate session | PASS | session `43` во всех четырёх наблюдениях, unique ids `[43]` |
| Mobile/desktop console, page, request и API errors | PASS, все `[]` | browser summary |
| Overflow, focus, reduced motion, loading/error states | PASS | browser summary и screenshots `00–07` |
| Primary touch targets ≥44 px | PASS | измерения от `48` до `56` px по высоте |
| Legacy cache-first Flutter SW мигрирует на current PWA | PASS | `legacy_worker_migration`: root SW/cache до, `/app/sw.js` после |
| Production image соответствует проверенному image | PASS | [`evidence/production-runtime.json`](evidence/production-runtime.json), 13/13 RootFS layers exact match |
| Реальные photo/Gemini и AI tutor после deploy | PASS | [`live-canary.json`](evidence/public-api-a6265c6/live-canary.json), [`vision.json`](evidence/public-api-a6265c6/vision.json) |

Синтетические phone/PIN из сохранённых API-artifacts удалены. Тестовые аккаунты не удалялись:
никаких деструктивных операций с production data не выполнялось.

## Mechanical gates

| Команда | Результат |
|---|---|
| `TEST_DATABASE_URL=<isolated-postgres> .venv/bin/pytest backend/tests/ -x -q` | `515 passed`, `22 warnings`, `60.28s`, exit `0` |
| `.venv/bin/pytest backend/tests/ -q` без DB URL | `370 passed`, `145 skipped`, exit `0`; skips — только DB integration gate |
| `npm exec vitest -- run` | `18` files, `96` tests passed, exit `0` |
| `npm run lint` | `0` errors, `3` ранее существовавших warnings, exit `0` |
| `npm run lint:design` | `114` files clean, exit `0` |
| `npm run build` | TypeScript + Vite production build + PWA precache `67` entries, exit `0` |
| `flutter analyze` | `No issues found`, exit `0` |
| `browser_student_start.py` против public URL | `PASS`, zero errors |

Три lint warnings не появились в release diff: это `react-refresh/only-export-components` в
`AuthContext.tsx` и `ConsentCard.tsx`, а также `react-hooks/exhaustive-deps` в `useRoutePath.ts`.

## Реальные AI-проверки

- Photo consent сначала отклонён сервером; corrupt upload получил ожидаемый validation error.
- Реальное фото прошло Gemini: grounded `mismatch`, confidence `1.0`.
- Отдельный vision set проверил и `match`, и `mismatch`: оба с confidence `1.0`, с первого раза.
- Tutor провёл multi-turn `2 → 4` messages, не выдал защищённый ответ и не ушёл в fallback.
- Полный lesson canary прошёл wrong-answer recovery, idempotent retry и завершение с
  `2` independent + `1` transfer заданиями.

## Deploy и rollback

- Local image: `kodi-web:onboarding-a6265c6`, linux/amd64,
  `sha256:60951509f7e4…`.
- Deployed config image: `sha256:267a39ed644b…`; config digest отличается после transfer/tag,
  но все `13` RootFS layer digests локально и на VPS совпадают побайтно.
- `/health` → `ok`; `/ready` → database, PWA и AI provider `true`.
- Production DB: duplicate non-null phone groups `0`; partial unique index присутствует.
- Release logs после старта: `0` Traceback/Unhandled/Uncaught/ERROR/CRITICAL/FATAL.
- Backup: `/home/eset/kodi-web/backups/20260716T084044Z-pre-onboarding.dump`, `909294` bytes,
  `pg_restore --list` дал `203` entries.
- Rollback image: `kodi-web:rollback-20260716T084044Z`.
- Tunnel `kodi-tunnel` сохранён, restart count `0`.

Проверенный endpoint сейчас — managed quick tunnel. `kodi.aiplus.kz` резолвится, но не обслуживает
этот release с доверенным TLS, поэтому документ не выдаёт его за рабочий canonical URL. Настройка
постоянного домена — отдельная infra-задача и не подменяет доказанный публичный deploy этой версии.

## Quality rubric

Повторный независимый blind review обновлённых post-deploy artifacts дал `READY`: critical gaps —
`0`, high gaps — `0`. Managed quick tunnel принят как публичный endpoint frozen gate; отсутствие
canonical domain не скрыто и не превращено задним числом в новый gate.

Итоговые оценки: time-to-learning `9.6`, decision clarity `9.2`, continuity `9.7`, error recovery
`9.2`, child readability `8.8`, mobile ergonomics `9.5`, trust `9.4`, production cohesion `9.4`;
среднее `9.35/10`, все оси выше frozen bar `8.0`.
