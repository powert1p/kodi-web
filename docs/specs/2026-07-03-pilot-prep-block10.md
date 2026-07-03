# Блок 1.0 — Пилот-подготовка (мини-срез · consent · телеметрия)

**Дата:** 2026-07-03 · **Слаг:** pilot-prep-block10

## Цель
Перед пилотом дать свежему ученику быстрый онбординг «пришёл → мини-срез → есть что разбирать», юридически закрыть сбор детских фото до первой фотографии и собрать сырую телеметрию поведения, чтобы после пилота считать воронку по фактам, а не по памяти.

## Scope
- Backend: колонки consent + таблица `events` (миграция в run.py + модели); эндпоинты `POST /srez/start`, `POST /srez/answer`, `POST /consent`, `POST /events`, `GET /events/export?format=csv`; 403 `consent_required` в `/diagnose`; поле `photo_consent` в `/auth/me` и в регистрации.
- Frontend: экран `/srez` (12 задач, фидбек Кёди, финал), CTA HubEmpty → `/srez`, чекбокс consent на шаге register-pin, consent-карточка на hub, обработка `consent_required` в drill, api-клиент + телеметрия-хелпер (fire-and-forget).

## Out-of-scope (НЕ делать)
- НЕ трогать diagnostic/exam FSM, mastery, BKT, build_wrong_tasks, граф. Срез — отдельный stateless-поток.
- НЕ делать UI-экран для экспорта событий (только CSV-эндпоинт владельцу). НЕ строить дашборд/аналитику по events.
- НЕ добавлять зависимости. НЕ полировать соседний код/тексты. НЕ реализовывать «вернулся»-метрику на клиенте.
- НЕ вводить Alembic. НЕ менять источники attempts у build_wrong_tasks.

## Продуктовые решения (приняты, не менять)
1. Мини-срез: сервер выдаёт 12 задач, клиент держит стейт; ответ пишется как `attempts(source="diagnostic")`; повторный проход разрешён (исключаем уже решавшиеся задачи). Ответ на задачу НЕ содержит correct_answer/solution.
2. Consent: чекбокс на register-pin (текст-черновик, «на проверку юристу»); существующим — мягкая карточка на hub («Разрешаю»/«Позже», «Позже» прячет до след. сессии через sessionStorage); фото-диагноз без согласия → 403 `consent_required`.
3. Телеметрия: batch ≤20/запрос, auth обязателен, неизвестные event_type пишем как есть; фронт шлёт fire-and-forget (ошибки глотать); экспорт CSV — только владельцу.
4. Тексты/комментарии на русском.

## Технические решения (обоснование одной строкой)
- Stateless-срез (нет in-memory state) — переживает рестарт, не конфликтует с single-worker-ограничением диагностики.
- `source="diagnostic"` в attempts — переиспользует контракт build_wrong_tasks без его изменения.
- Выбор задач: `DISTINCT ON (COALESCE(topic_id,node_id))` + `has_decomp DESC, difficulty ASC` — разброс тем, лёгкие первыми, decomp-линк мягко предпочтён (fallback на любые).
- answer_type-фильтр: `NULL / number / integer / fraction / decimal / float` — исключает choice/text (не набираются с клавиатуры).
- Батч + fire-and-forget телеметрия — не роняет и не тормозит UX пилота.
- 403 `consent_required` на `/diagnose` (не на регистрации) — сбор фото гейтится непосредственно перед первой фотографией.
- CSV-экспорт вместо экрана — потребитель один (владелец), пилотный анализ в таблицах.

## Файлы
- `backend/db/models.py` — модель `Event`; поля `Student.photo_consent`, `Student.photo_consent_at`.
- `backend/run.py` — ALTER students (2 колонки) в список ALTER; CREATE TABLE events + индекс в список CREATE.
- `backend/api/routes.py` — `PhoneRegisterBody.photo_consent`; запись consent при регистрации; `photo_consent` в `/auth/me`.
- `backend/api/routers/trainer.py` — новые эндпоинты srez/consent/events/export; 403 в начале `post_diagnose`.
- `webapp/src/lib/{api,auth,types}.ts`, `webapp/src/lib/telemetry.ts` — клиент + хуки + хелпер трекинга.
- `webapp/src/App.tsx`, `webapp/src/features/srez/*` — маршрут и экран `/srez`.
- `webapp/src/features/hub/HubEmpty.tsx`, `.../hub/ConsentCard.tsx`, `HubPage.tsx` — CTA + consent-карточка.
- `webapp/src/features/auth/{LoginPage,AuthContext}.tsx` — чекбокс consent; проброс в register.

## Критерии успеха (проверяемые)
- pytest зелёный: юнит выбора среза (разброс тем · difficulty ASC · исключение решённых · предпочтение decomp) + integration srez start/answer (attempt записан, ответ без correct_answer, wrong-tasks непуст после неверного) + consent (403 без согласия, 200 после) + events (batch insert, export owner-only 403/200). Все существующие тесты остаются зелёными.
- `npx tsc --noEmit`, `npm run lint:design`, `npm run build`, vitest — зелёные.
- Скриншоты 390×844: экран среза (задача + прогресс), hub с consent-карточкой.
- E2E: свежий ученик → hub «мини-срез» → 12 задач с ошибками → wrong-tasks непуст → drill открывается.

## Риски
- Мало лёгких decomp-задач на свежей БД → предпочтение мягкое (сортировка, не фильтр); при нехватке тем срез < 12 — допустимо для пилота.
- check_answer на свободном вводе детей (запятые/пробелы) → полагаемся на существующую нормализацию `_normalise`, новую не пишем.
- Спам событиями → rate-limit slowapi + cap 20/batch; заметим по 429/росту таблицы events.
- topic_id не заполнен на части узлов → COALESCE на node_id даёт fallback-разброс, не пустой результат.
