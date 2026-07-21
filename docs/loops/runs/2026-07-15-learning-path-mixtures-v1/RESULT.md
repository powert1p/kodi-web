# Learning path v1 «Мой путь» — результат

**Status:** READY locally · **URL:** http://localhost:8400/app/ · **Login:** `+70000000000` / `0000`

## Что изменилось

Корневой сценарий больше не построен вокруг дневной очереди и «закрытия ошибок». `/app/` показывает накопительный учебный путь: курс «Подготовка к НИШ» → текущий блок «Смеси и концентрации» → один конкретный следующий урок. Прогресс подписан в scope блока, поэтому `0 из 1` не выдаётся за прогресс всего курса.

- На первом mobile viewport видны следующий урок, его цель, длительность и одна primary action; фото, чат, review и mascot не конкурируют с математикой.
- Внутри урока ребёнок проходит `Разобрать → Доделать → Решить → Перенести`, а semantic phase определяется текущей activity role.
- Подсказка появляется только после попытки, относится к текущему micro-skill и не раскрывает ответ.
- Прогресс, попытки, восстановление draft и итоговый evidence server-owned и переживают reload.
- Предыдущий многофункциональный hub оставлен в `/app/review` для осознанного доступа.

## Продукт и реализация

- Curriculum manifest теперь содержит явный contract пути и текущего блока; API — `GET /api/learning/path/current`.
- `LearningSession` и `LearningAttempt` сохраняются с idempotent answer submission.
- Stale-state защищён `activity_id` + `activity_index` под lock и authoritative `409` recovery.
- Frontend requests scoped по identity, поэтому поздний response не откатывает более новый state и не протекает между аккаунтами.
- Stable `content_idx` и canonical problem synchronization безопасно обновляют существующую БД.
- Ambiguous same-node или answer-only decomposition fallback остаётся fail-closed.

## Research transfer

Структура урока переносит полезные механики из Anthropic teacher work, а не копирует generic chat UI: named prerequisite и target skills, concrete-representational-abstract sequencing, fading supports, transfer, structural cases и один canonical source. Mapping и exclusions записаны в [`ANTHROPIC-TRANSFER.md`](ANTHROPIC-TRANSFER.md).

## Проверка

- Backend: `176 passed`; manifest uniqueness/public-summary и explicit `lesson_id` regression-gates включены.
- Frontend: oxlint pass с тремя pre-existing warnings; design lint `109 files`; TypeScript pass; Vitest `15 files / 89 passed`; production build pass.
- Production E2E: `18 screenshots` на 375×844 и 1280×900; console/page/request/API error arrays пусты.
- Frozen path evidence: `19/19` hashes.
- Own-eyes: path до и после завершения (`0/1 → 1/1`), lesson, wrong-answer support, reload recovery, network-preserved answer, result, error и empty просмотрены в реальных renders.
- Independent post-fix code re-review: `CLEAN/READY`.
- Blind production panel: `READY` 3/3 (`9.60`, `9.40`, `9.36`; среднее `9.45`), `working_product=true` 3/3, без high/medium delta.

Полный gate: [`PRODUCTION-GATE.md`](PRODUCTION-GATE.md). Browser evidence: [`production-evidence-path/`](production-evidence-path/).

## Честная граница

Это production-shaped первый vertical, а не весь curriculum. Сейчас в текущем блоке authored один полноценный урок, поэтому интерфейс честно показывает `0 из 1` до работы и `1 из 1` после результата, а не рисует фиктивную длинную дорожку. Следующий продуктовый шаг — уроки 2+ по тому же manifest/evidence contract и выбор следующего named skill по mastery, без возврата к случайным лёгким задачам.
