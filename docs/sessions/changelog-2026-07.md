# Сессии — 2026-07

## 2026-07-07 18:09
**Тип:** plan (вердикт `docs/specs/2026-07-06-graph-topic-audit-verdict.md`, КТП `docs/plan/ktp-v1.md`)
**Зачем:** владелец (ультра-мандат: effort+ultracode+workflow) попросил перепроверить логику графа на уровне ТЕМ («темы между собой бьются?») и построить структуру обучения под схему центра: теория — живой учитель, практика — AI с фото-сдачей шагов.
**Что сделано:** (1) Workflow-аудит 60 агентов: 8 линз (6 strand-зон + цикл + coverage, sonnet) → 52 находки → adversarial verify каждой на opus → 22 подтверждено/28 опровергнуто/2 рассужены вручную; спорные фиксы адьюдицированы Fable по реальным задачам БД. (2) Патч v03 (data-engineer по вердикту): −6 рёбер (AR09→CV04/CV05, GE01→GE12, EQ02→WP03, DV02→LG04, AL01→EQ02-транзитив), +3 (AL02→EQ02, DC01→AR07, AR10→LG04), 3 имени тем, 5 переносов задач с текст-гардами; JSON+dev+ПРОД (pg_dump-бэкап, атомарная транзакция, пост-ассерты, идемпотентность 0 на повторе; денорм-каскад включая decomposition-банк). (3) КТП v1: 13 учебных блоков, покрытие 114 узлов/2525 задач, порядок блоков проверен программно против рёбер (0 нарушений), цикл занятия учитель↔AI, гейты выхода, экзамен-трек НИШ надстройкой.
**Решение:** перепривязки AR01/AR08 ОТКЛОНЕНЫ (контент-аргументы сильнее: CC-канон и реальный состав задач) — два тематических знота ({3.OA.A,3.OA.B,4.NBT.B,5.OA.A} и {6.NS.C,7.EE.A,7.EE.B}) ведутся в КТП едиными блоками; узловой граф был и остаётся DAG (Kahn 114/114); мультикласс + универсальные блоки без недель (выбор владельца).
**Итог:** прод мигрирован: 114 узлов/178 рёбер, входы узлов ожидаемые, темы переименованы, 5 задач на новых узлах; 140 pytest (гейт test_graph_semantics обновлён 181→178 + точечные v03-ассерты); ревью READY; merge ff → main, push.
**Открытые вопросы:** 7 тем-сирот в прод-БД (43 vs 36; скрыты фильтром, ждут одобренного DELETE); бэклог КТП: выгрузка «прогресс группы по блоку» для учителя, повторный срез по пройденному, блочный прогресс в UI; LLM-заход на остаток утечек ответа (~4.8k) не начат.
**Файлы:** docs/specs/2026-07-06-graph-topic-audit-verdict.md, docs/plan/ktp-v1.md, backend/scripts/{apply_graph_v03,migrate_graph_v03_db}.py, backend/tests/test_graph_semantics.py, backend/data/*.json
**Issue:** —

## 2026-07-06 14:28
**Тип:** ad-hoc (показ владельцу + хвост автономной смены)
**Зачем:** владелец спросил «сайт готов? покажи» — живой показ прода; заодно домержен хвост: eval-стенд Блока 1.1, бэклог-мелочи, найденный на показе SPA-гэп.
**Что сделано:** (1) витрина-артефакт с 4 живыми скринами прода (хаб / срез / drill Ввод / drill По тетради) — https://claude.ai/code/artifact/7544de8a-94a7-4f28-9aa1-327a1f2c3be5; (2) eval-стенд `backend/scripts/eval_stand.py` (+генератор синтетики, тесты, README) — метрики accuracy/false-reject, синтетический smoke 7/7 живым Gemini; (3) мелочи: seed_demo scalar, dead import+docstring, in-flight guard closure; (4) SPA-fallback `SPAStaticFiles` в web.py — прямые ссылки/refresh внутри PWA (`/app/srez`) больше не 404 (найдено на показе, проверено на проде).
**Решение:** fallback только для путей без расширения — ассеты остаются честным 404; фолбэк отдаёт литеральный index.html (без user-контролируемого пути — traversal исключён).
**Итог:** батч-ревью READY TO MERGE; 137 pytest; прод: health 200, дип-линк отдаёт index, ассет 404. Merge ff → main (5543ccc), push.
**Открытые вопросы:** сбор 30-50 реальных фото тетрадей (владелец, README в data/eval); маркетинговый «сайт»-лендинг не существует — есть PWA-продукт (домен+SSL ждут root/Умида).
**Файлы:** backend/web.py, backend/scripts/eval_stand.py, backend/data/eval/README.md, webapp/src/features/closure/useClosure.ts
**Issue:** —

## 2026-07-04 00:55
**Тип:** bug-fix (данные банка)
**Зачем:** P1 контент-баг: 49% текстов ступеней лесенки содержали ответ («Сложи 23 и 45: 23 + 45 = 68») — тренажёр подсказывал решение до попытки; баг всплыл прямо в live-срезе Блока 1.0.
**Что сделано:** скрипт `backend/scripts/fix_step_answer_leaks.py` (audit/apply/apply-json, бэкапы, идемпотентность) + table-driven тесты. Вычищена безопасная категория — числовой «= ответ» в абсолютном конце при вычислимом выражении перед ним: 1266/7036 ступеней (18%) в dev-БД, JSON-банке и ПРОД-БД (повторный apply = 0).
**Решение:** тупая массовая regex-правка отклонена — аудит показал 3 опасных категории (mid-sentence «= 36 яблок» 3929 шт., ev-выражения «(100−1)×15» 648 шт., суперскрипты «2⁶=64» 260 шт.), где срез ломает педагогику или уравнения («x² = 49»). Их правка = LLM-заход с судейством (бэклог с цифрами). Правка контента — с CSV-бэкапом до UPDATE (dev и прод: `~/kodi-web/backups/` на aiplus).
**Итог:** прод live: ступень задачи среза больше не содержит «= 68» (проверено API). 124 pytest. Merge → main, push.
**Открытые вопросы:** LLM-заход на остальные ~4.8k утечек (нужно переписывание текста, не regex); бэкап-CSV хранится 1 копией на сервере.
**Файлы:** backend/scripts/fix_step_answer_leaks.py, backend/data/full_decomposition_v1.json
**Issue:** —

## 2026-07-04 00:36
**Тип:** plan (спека `docs/specs/2026-07-03-step-submit-block12.md`, план `docs/superpowers/plans/2026-07-03-step-submit-block12.md`)
**Зачем:** Блок 1.2 мастер-плана «Поэтапная сдача» — ядро MVP стартапа: ребёнок решает в тетради по ступеням лесенки и сдаёт фото КАЖДОГО шага; система классифицирует (не транскрибирует) и копит датасет фото+шаг+вердикт. Продолжение автономной ночной сессии (после Блока 1.0).
**Что сделано:** 7 SDD-тасок: (1) таблица `step_submissions` (датасет: student/decomp_idx/step_n/verdict/confidence/photo_path); (2) `classify_step_photo()` — узкая vision-классификация (строгая json_schema verdict match|mismatch|unsure, реюз model_chain/strict-fallback diagnose_photo); (3) `POST /trainer/step-submit` (гейты consent-403/413/415/503/rate-limit, фото после commit в `error_photos/steps/`); (4) owner-эндпоинты export CSV + step-photo; (5) FE `useStepSubmitFlow`; (6) режим «По тетради» в drill (тумблер, сдача ступени фото, unsure=«сфотай ещё раз» без штрафа, мост в ladder без правки машины); (7) E2E + добивка security-тестов. Плюс 2 деплой-фикса: max_tokens 256→1024 (thinking-токены gemini обрезали JSON на реальных фото — найдено E2E) и bind-mount `error_photos` (датасет не переживал rebuild контейнера).
**Решение:** классификация вместо транскрипции (принцип VISION.md — 87% ошибок моделей это чтение); мягкость: mismatch с confidence<0.6 → unsure, unsure НЕ ошибка и не двигает wrongStreak (false-reject хуже пропуска); ladder.ts не тронут — мост drill.submit(expected_value)/(сентинел 'nomatch'), значения юзеру не видны (проверено ревью до рендера); choose-ступени остаются интерактивными в фото-режиме; seen_value клиенту не отдаётся (утечка соседнего шага); Блок 1.1 (eval-набор) НЕ блокер — порог уточнится по его данным.
**Итог:** задеплоено и live-проверено на проде реальным Gemini: «23+45=68» → match confidence 1.0, «23+45=58» → mismatch 1.0; строки в step_submissions + фото на диске (volume); health 200; миграция existing-БД ок. 121 pytest + 50 vitest + tsc/lint:design/build чистые. Merge ff → main (0afb56c), push.
**Открытые вопросы:** rate-limit 15/min на step-submit может жать усердного ребёнка (429 → generic-текст); seen_value можно копить в датасет (owner-only) для будущего файнтюна; STEP_CONFIDENCE_THRESHOLD=0.6 ждёт калибровки Блоком 1.1; P1 контент-баг банка (ступень палит ответ «23 + 45 = 68») — виден прямо в live-срезе, следующий кусок; DEV-мок wrong-tasks маскирует пустой hub.
**Файлы:** backend/core/llm_openai.py, backend/api/routers/trainer.py, backend/db/models.py, webapp/src/features/drill/StepModeToggle.tsx, StepSubmitPanel.tsx, useStepSubmitFlow.ts, docker-compose.yml
**Issue:** —

## 2026-07-03 20:35
**Тип:** plan (спека `docs/specs/2026-07-03-pilot-prep-block10.md`, план `docs/superpowers/plans/2026-07-03-pilot-prep-block10.md`)
**Зачем:** Блок 1.0 мастер-плана «Пилот-подготовка»: свежий ученик упирался в «Всё разобрано» (нет источника ошибок в PWA), сбор детских фото юридически не закрыт, поведение пилота нечем мерить. Владелец на выходных — заход полностью автономный (вопросы запрещены, развилки решал оркестратор).
**Что сделано:** 8 SDD-тасок (sonnet-имплементеры/ui-designer + opus-ревью на каждую): (1) миграция — таблица `events` + `students.photo_consent/_at` (create_all + идемпотентные ALTER в run.py, прод-БД мигрировала стартом контейнера); (2) consent: `POST /trainer/consent`, 403 `consent_required` в /diagnose, чекбокс на регистрации, hub-карточка «Спросим родителя» (вариант hub — компакт/secondary/без маскота; drill — Кёди+primary, контракт в канон §3); (3) мини-срез: `POST /srez/start` (12 задач: DISTINCT ON темы, difficulty ASC, мягкое предпочтение decomp-линка, исключение решавшихся, только typeable answer_type) + `/srez/answer` (check_answer → attempts source="diagnostic", без утечки ответа) + экран `/srez` (прогресс, фидбек Кёди, финал «Нашли N тем»); (4) телеметрия: `POST /events` batch (received/inserted честно) + owner-only CSV-экспорт + 9 событий по экранам; (5) `OWNER_STUDENT_ID` прокинут в compose (была та же граблина, что с GEMINI_API_KEY).
**Решение:** мини-срез = отдельный stateless-поток, НЕ diagnostic/exam FSM (те считают темы×вопросы=30-60 и пишут mastery/diagnostic_complete — побочки); снятый чекбокс = NULL «не ответил» (false ломал бы «спросить позже»); inputMode="text" универсально (в банке дроби и 75 отрицательных ответов — iOS decimal без «/» и «−»); телеметрия fire-and-forget (track() никогда не кидает).
**Итог:** задеплоено и live-проверено на проде: health 200, миграция existing-БД ок, срез отдаёт 12 задач без утечки ответа, неверный ответ → wrong-tasks, diagnose 403 consent_required → грант → me:true, events пишутся (hub_opened/srez_started в прод-БД), не-owner экспорт 403, «Мини-срез» в бандле. 98 pytest + 46 vitest + tsc/lint:design/build чистые. E2E локально ALL PASS. Merge ff → main (8bdd74b), push.
**Открытые вопросы:** текст consent-чекбокса — юристу; срез на проде выдал задачу «23+45» с ответом в банке — прогнать P1-аудит утечки ответов в текстах ступеней (бэклог); DEV mock-fallback wrong-tasks маскирует пустой hub в dev; двойной сабмит srez/answer пишет 2 attempts (дедуп в wrong-tasks есть, аналитика может задвоить).
**Файлы:** backend/core/srez.py, backend/api/routers/trainer.py, backend/db/models.py, backend/run.py, webapp/src/features/srez/*, webapp/src/features/hub/ConsentCard.tsx, webapp/src/lib/telemetry.ts, docker-compose.yml
**Issue:** —

## 2026-07-03 17:23
**Тип:** plan (research `docs/specs/2026-07-03-research-ai-design.md`, канон `webapp/DESIGN_SYSTEM.md` v5, план `docs/plan/master-plan.md`)
**Зачем:** после 2026-07-07 нет Fable в подписке — Opus один не вытягивает дизайн («ужасный получается»). Нужно: research «качественный дизайн с ИИ», дизайн-система как рельсы «Opus не испортит», максимально детальный мастер-план Opus-эпохи со сценариями.
**Что сделано:** (1) deep research 5 кластеров (природа AI-slop / система-как-рельсы / workflow / tween-UX 10-13 / операционализация) + честный скриншот-аудит текущего PWA (18 скринов, ~5.5/10: ID-утечки в UI, «46 ₽», мёртвые пустоты, ноль адаптации >390px); (2) DESIGN_SYSTEM v5 (директор — Fable): Golos Text вместо DM Sans+Onest, paper-подложка, «оранжевый = только действие», 8 NEVER-запретов, закрытые контракты Ap*, Кёди-протокол (4 момента), дизайн-протокол постановки задач Opus'у; (3) внедрение двумя агентами (57+15 файлов): токены/шрифт/экраны + label_ru через все эндпоинты + `npm run lint:design` (гейт: hex/px/полушаги/шрифты → exit 1) + baseline-скриншоты в `webapp/design-baselines/`; (4) мастер-план: очередь блоков этапа 1, сценарные развилки A-D, правила эпохи.
**Решение:** slop лечится сужением выбора ДО генерации, не промптом («инструкция не переживает свежий контекст — переживает то, что не проходит гейт»); эстетика фиксируется директором один раз, Opus только исполняет по эталонам; критика — всегда отдельным вызовом (самопроверка −20-40 п.п.); tween-дизайн = спокойный+тёплый, ошибки голосом Кёди, прогресс>стрики.
**Итог:** задеплоено на прод: health 200, label человеческие в API («Сложение и вычитание целых чисел» вместо int_add_sub), Golos Text в бандле; ревью волны нашло 1 функциональную регрессию (маскировалась моком) — исправлена; 87 pytest + 43 vitest + lint:design чист. Merge ff → main, push.
**Открытые вопросы:** P1 контент-баг банка (текст ступени палит ответ «63+28=91») — скрипт-аудит+правка; axe-гейт не подключён (§7 канона); FinishedCard полный v5-проход; Playwright toHaveScreenshot-тесты против baselines не автоматизированы (baseline'ы есть).
**Файлы:** webapp/DESIGN_SYSTEM.md, webapp/scripts/lint-design.mjs, webapp/design-baselines/, docs/plan/master-plan.md, docs/specs/2026-07-03-research-ai-design.md
**Issue:** —

## 2026-07-03 15:01
**Тип:** plan (research `docs/specs/2026-07-03-research-photo-to-live-tutor.md`, видение `docs/VISION.md`)
**Зачем:** тренажёр переключается в идею стартапа (оффлайн-центр: учитель объясняет, AI ведёт индивидуальную практику; северная звезда — live-наблюдение за решением на планшете + голос). Нужно: закрепить видение как постоянный контекст, deep research пути, роадмап этапов, чистка репо к стартап-фазе.
**Что сделано:** (1) deep research — 6 параллельных кластеров (детский мат-OCR / поэтапная проверка / live-ink / голос / данные+приватность / бизнес-референсы) + red-team на Opus (5 Critical, 6 Important — все внесены; 3 несущие arXiv-цитаты верифицированы вручную); (2) VISION.md: продукт, бизнес-рамка, 5 несущих техпринципов, роадмап 5 этапов с гейтами, топ-риски — вшит в CLAUDE.md/PROJECT.md/plan; (3) чистка: 87 файлов dead code удалено (scorers/classifiers 41, cabinet/src 44, дубль decomposition-JSON + мёртвый fallback), 9 в архив, gitignore для артефактов/фото учеников, 33 PNG+webapp_dist с диска; (4) доки актуализированы (module-map 18 таблиц/13 core-модулей/граф v02).
**Решение:** классификация шагов против verified-банка вместо транскрипции почерка (87% ошибок моделей — чтение; grounding — главный рычаг); поэтапная сдача = ядро, но d=0.76 не переносится на async-фото (эффект MVP скромнее — честно зафиксировано); риск №1 — бизнесовый (retention/чит дома), не технический → behavioral-пилот на семьях центра ПЕРВЫМ шагом этапа 1; юр-гейт шире consent (локализация данных РК → юрист до сбора).
**Итог:** задеплоено (health 200, данные целы 114/2525), merge ff → main, push. Research red-team'нут, видение в контексте каждой будущей сессии.
**Открытые вопросы:** судьба `cabinet/src/mock/srez.ts` (WIP владельца, единственный выживший из cabinet/src); anti-copy механика (вариативные параметры задач); юр-консультация по трансграничной передаче; Этап 1 «Поэтапная сдача» — следующий большой заход.
**Файлы:** docs/VISION.md, docs/specs/2026-07-03-research-photo-to-live-tutor.md, docs/_archive/2026-07/, backend/db/seed_decomposition.py
**Issue:** —

## 2026-07-03 12:43
**Тип:** plan (вердикт `docs/specs/2026-07-03-graph-v02-verdict.md`)
**Зачем:** качество графа знаний — контент генерился Опусом одним blob'ом без валидации: рёбра-пререквизиты с ложной логикой, привязки узлов к темам врали о содержании, дубль-ветка из 4 узлов, stale-метаданные. Владелец явно попросил ручной проход Fable, без делегирования судейства.
**Что сделано:** ручной проход по всем 118 узлам / 200 рёбрам / 118 привязкам с опорой на реальные задачи → вердикт-файл: 28 DROP + 15 ADD рёбер (принципы: prereq живёт только если без него задачи нерешаемы; transitive reduction), 7 RETAG узел→тема (напр. «Действия с десятичными» жила в теме «НОД и НОК»), снос дубль-ветки NM01/NM02/NM03/ALG01 с перепривязкой 73 задач (по правилу «модуль→MD01») синхронно в problems_v10 + decomposition-банке + БД. Механика — агентами: apply-скрипт, семантический тест-гейт (ацикличность/сироты/пустые темы/счётчики — 8 тестов), миграция existing-БД одной транзакцией с гейтом против SEED-1-дрейфа.
**Решение:** валидация+правка вместо радикальной пересборки (сохраняет работающую диагностику/экзамен); пустые темы убраны из JSON (36 непустых), сироты в прод-БД оставлены (скрыты фильтром, cleanup при следующем одобрении); дев-БД пересобрана с нуля (одобрено — была битая SEED-1: 1794/2525 задач).
**Итог:** задеплоено и мигрировано: прод 114 узлов/181 ребро/36 тем, миграция 73+73 перепривязки/0 потерь, пост-ассерты OK; live: graph/me отдаёт 114/181/36 без пустых тем, тренажёр (wrong-tasks/problem-topics) живой; 85 pytest зелёные; merge ff → main, push. Ревью: ready-to-merge, 1 warning (stale node_id в problem_reports/tutor_sessions) проверен фактикой — 0 строк, не материализовался.
**Открытые вопросы:** CB02≈CB04 — дубль навыка «размещения без повторений» (кандидат на слияние); recurring_errors при будущих сносах узлов маппится без модуль-эвристики (нет текста задачи); 7 тем-сирот в прод-БД ждут одобренного cleanup; косяки задач (FR05 требует десятичных, DA02 с «ускорением», EQ06-пример = EQ07).
**Файлы:** docs/specs/2026-07-03-graph-v02-verdict.md, backend/scripts/{apply_graph_v02,migrate_graph_v02_db}.py, backend/tests/test_graph_semantics.py, backend/data/*.json
**Issue:** —


## 2026-07-02 17:10
**Тип:** plan (спека `docs/specs/2026-07-02-error-trainer-backend-core.md`, план `docs/superpowers/plans/2026-07-02-error-trainer-backend-core.md`)
**Зачем:** тренажёр работал по кускам (closure на моке, analytics рассинхронен, после диагноза ученик один на один с ошибкой) + «каша из двух графов» — тренажёр группировал по старым 15 плоским доменам, граф — по CC-слою. Нужна бэк-основа, которая даёт ИИ-агенту максимум контекста, и полный флоу до закрытия ошибки.
**Что сделано:** 11 тасок SDD (Sonnet-имплементеры + Opus-ревью на каждую): 2 таблицы `tutor_sessions/tutor_messages`; `core/agent_context.py` (context-pack: задача+шаги+fingerprints+история+mastery+тема — единый grounding для diagnose и чата); `core/tutor.py` + `POST /tutor/chat` (multi-turn, сократический, rate-limit 15/min, 503 на LlmUnavailable, UNIQUE против гонки сессий); `GET /problem-topics` (агрегат error_captures→problems.node_id→nodes.topic_id→topics, SQL-инвариант-тест); `POST /verification/start|answer` (closure на живых данных, resolved по node_id); `GET /easier` (climb-down); PWA: блок «Мои проблемные темы» в hub, TutorPanel в drill, closure/analytics на живом API.
**Решение:** каноническая таксономия = CC-слой (strand→topic→node→micro_skill); `node.tag`/`micro_skills.domain` — deprecated legacy, не удалены; remap 372→337 НЕ делаем (архив `cc_topic_skill_tree.json`) — тронул бы прод-данные ради нулевой ценности. «Граф проблемных тем» = агрегат над существующими таблицами, без новых графовых структур. Чат в БД, без стриминга (MVP).
**Итог:** задеплоено на aiplus и проверено live: /health 200; `problem-topics` отдаёт 4.NBT.B; tutor/chat — живой Gemini (Кёди, сократика, ответ не раскрыт), session reuse (id=1), history 2→4. Локальный E2E ALL PASS (7 скриншотов, 0 console errors): hub→drill→фото→диагноз→чат→closure («Ошибка закрыта!», тема 0%→100% без перезагрузки, recurring_errors.resolved=t)→analytics my_top. Тесты: 77 pytest (реальный PG, 0 skip) + 43 vitest + build чистый. Merge ff в main (15dea9f), запушено в origin.
**Открытые вопросы:** wrong-tasks не скрывает закрытые ошибки («Закрыто 0 из 2» при закрытой теме) — продуктовое решение нужно; FinishedCard «46 ₽» (валютный формат на арифметике); seed_demo.py `.scalar()` дважды; dead code (resolve_decomp import F401, analytics/mock.ts, fetchEasier без консьюмера — climb-down UI не подключён); ru+kz parity; публичный vhost (root).
**Файлы:** backend/core/{agent_context,tutor,trainer}.py, backend/api/routers/trainer.py, webapp/src/features/{hub/ProblemTopicsCard,drill/TutorPanel,closure/*}.tsx
**Issue:** —

## 2026-07-10 19:05
**Тип:** plan (ТЗ MVP, Заход 1)
**Зачем:** владелец протыкал прод и вынес вердикт «всё сыро»: срез примитивный, бота не спросишь, теории нет, две точки сдачи, фейковые плашки. MVP переопределён: «ребёнок начал учиться и было полезно».
**Что сделано:** ТЗ `docs/specs/2026-07-10-mvp-nish-path.md`; Заход 1 целиком: онбординг новичка (has_activity), класс при регистрации + срез v2 по difficulty-окну класса, теория «Как решать» на 114/114 узлов (генерация батчами, 10 карточек принято лично) → nodes.theory_ru → drill, тьютор-grounding (метод узла + step_n + 6 жёстких правил), возврат чата Кёди в drill, один вход сдачи, фолбэк-ступень для задач без декомпозиции, backfill теории на старте контейнера.
**Решение:** теорию на прод доставляем НЕ ручным скриптом, а идемпотентным backfill_theory в run.py из запечённого в образ graph-JSON (по образцу seed_topics) — ноль ручных шагов деплоя; карточки-исходники gitignored. Деплой-факап: tar-поверх не удаляет удалённые из git файлы → стейловый useDiagnoseFlow.ts валил tsc в Docker; правило «rm -rf webapp backend перед распаковкой» зафиксировано в .claude/rules/deploy.md.
**Итог:** задеплоено и live-проверено на проде свежим аккаунтом «иду в 7»: срез 12/12 задач difficulty ≥3 (0 примитива), регистрация с обязательным классом, теория раскрывается в drill, чат e2e — метод+встречный вопрос, ответ под выпрашиванием не выдал; консоль чистая. Ревью opus: READY_WITH_MINOR (step_n ge=1 починен). Гейты: 153 pytest, 52 vitest, lint:design, build. Merge ff → main (c9bdc6c), push.
**Открытые вопросы:** Заход 2 «Мой путь» (13 КТП-блоков + практика узла с mastery-гейтом); минорки ревью (мёртвый diagnose-путь, drill.png baseline); хвост банка: 57 steps-батчей (Codex CLI) + унифицированный фикс-скрипт (~17 ответов, ~17 broken, ~650 утечек).
**Файлы:** docs/specs/2026-07-10-mvp-nish-path.md, backend/core/srez.py, backend/core/tutor.py, backend/db/seed.py, backend/scripts/seed_theory.py, webapp/src/features/drill/TheoryCard.tsx, webapp/src/features/auth/GradeSelect.tsx
**Issue:** —

## 2026-07-14 18:02
**Тип:** plan (закрытие redesign-run 2026-07-13-webapp-v6)
**Зачем:** «сделай очень красивый дизайн топового уровня» — редизайн мобильного тренажёра (webapp/) по новому дизайн-флоу владельца (design-lab FLOW v3) режимом «цикл до планки».
**Что сделано:** 4 раунда benchmark-loop (3 концепта → порт → 2 фикс-раунда, 19 fix/feat-коммитов); v6 «Тетрадь чемпиона»: токены слоёв бумаги+клетка, два оранжа (brand/route-line), Unbounded+Golos self-hosted, сквозная сигнатура «маршрут маркером» (3 статических слоя), KaTeX в sans. Канон запечён в webapp/DESIGN_SYSTEM.md, baselines пересняты, RESULT.md + FLOW-CHANGELOG (8 докруток генератора). Деплой на aiplus, live-проверка прод-скринами.
**Решение:** бюджет 4 раундов выбит → стоп по контракту с честной фиксацией: планка СУПЕР формально не взята (R3 полная панель avg 8.21, wow 2/3, один SUPER; R4-партиал J1 7.88 wow / J2 8.38 wow, J3 убит лимитом сессии), остаточные дельты → бэклог в RESULT.md. Канон-гравитация нейтрализована ДО имплементации (фидбек владельца: стейл DESIGN_SYSTEM/память тянули агентов в старый вид).
**Итог:** задеплоено — http://195.49.215.96:8300/app/ (health 200, сид идемпотентен; login-трейлхед и hub «12 из 12» с маршрутом проверены глазами на проде). main = fff4e3d, запушено.
**Открытые вопросы:** 7 остаточных дизайн-дельт (RESULT.md §бэклог); Заход 2 «Мой путь»; хвост аудита банка; мёртвый diagnose-путь.
**Файлы:** webapp/src/theme/tokens.css, webapp/src/components/route/*, webapp/DESIGN_SYSTEM.md, docs/loops/runs/2026-07-13-webapp-v6/RESULT.md
**Issue:** —

<!-- codex-wrap:9aefacdebc55b53e733e:begin -->
## 2026-07-17 - Adaptive photo-first NIS production release

- Why: Довести регистрацию нового ученика до полноценного адаптивного обучения: карта экзамена, диагностика, персональный маршрут, photo-first самостоятельное решение и guided-разбор только по явному запросу.
- Result: Production доступен на https://observer-terrorists-reputation-chosen.trycloudflare.com; регистрация, адаптация, диагностика, разные персональные маршруты, exact resume, unreadable/incorrect/correct photo verdicts и mastery после 3/4 самостоятельных решений подтверждены end-to-end.
- Next: Провести первую наблюдаемую учебную сессию с реальным учеником и сравнить его затруднения с зафиксированным production CJM.
<!-- codex-wrap:9aefacdebc55b53e733e:end -->

<!-- codex-wrap:e2cb4ce4da7fb9b0d7a0:begin -->
## 2026-07-17 - Приём корректного HEIC-решения дробей

- Why: Читаемое решение сравнения дробей отклонялось из-за слишком строгого сопоставления вариативного OCR с canonical steps.
- Result: Исходный IMG_4978 HEIC на production пять раз подряд получил verdict correct с evidence_verified=true; сервис healthy и публичный ready зелёный.
- Next: Повторно отправить тот же снимок из интерфейса ученика; переснимать страницу больше не требуется.
<!-- codex-wrap:e2cb4ce4da7fb9b0d7a0:end -->

<!-- codex-wrap:c2d482f49d2b4c85c2d7:begin -->
## 2026-07-17 - AI-owned проверка фото решения r16

- Why: Корректное рукописное решение IMG_4979.heic отклонялось из-за backend-проверки, которая не соответствовала продуктовому контракту AI-owned grading.
- Result: r16 развёрнут image-only на production. IMG_4979.heic принят 3/3 для исходной задачи и отклонён 4/4 на обратном вопросе с failed_step=3; public app healthy и AI provider ready.
- Next: На первой реальной учебной сессии проверить долю correct/incorrect/unsure на новых рукописных фото и разбирать только bounded evidence случаев unsure.
<!-- codex-wrap:c2d482f49d2b4c85c2d7:end -->

<!-- codex-wrap:42fc9847a5633347a518:begin -->
## 2026-07-17 - Unified learning workspace design freeze

- Why: Убрать полноэкранные переходы и собрать implementation-ready учебный UX с photo-first проверкой, typed-альтернативой, контекстным AI tutor и корректной mastery-семантикой.
- Result: Готовы BRIEF, CJM, state map, AI UX contract, selected concept, 30 проверенных renders и dependency-ordered implementation backlog P0-P6. Production code и deploy намеренно не менялись в этом Goal.
- Next: Создать следующий Goal на P0-P3: ADR и canonical docs, versioned journey workspace envelope, AI semantic services и durable support/resume state с backend tests.
<!-- codex-wrap:42fc9847a5633347a518:end -->

<!-- codex-wrap:08e50303bd8098ebbe38:begin -->
## 2026-07-17 - AI-owned grading и journey workspace envelope v1

- Why: Убрать backend exact-checker из semantic verdict и дать клиенту единое versioned состояние задачи вместо разрозненных переходов.
- Result: AI владеет correct/needs_revision/uncertain, backend fail-closed валидирует результат; task, photo evidence, context, response capabilities, support и revision формируются из одного journey state, включая transfer retry и stale-revision recovery.
- Next: P2: подключить React JourneyPage к hasJourneyWorkspace и собрать один стабильный учебный экран без переходов между отдельными страницами.
<!-- codex-wrap:08e50303bd8098ebbe38:end -->

<!-- codex-wrap:1236e4a74b02ad29223d:begin -->
## 2026-07-17 - Unified learning workspace r20 production release

- Why: Собрать разрозненные учебные экраны в один непрерывный рабочий флоу, передать смысловую проверку фото Gemini и довести приложение до проверенного production-состояния.
- Result: Production r20 доступен на https://observer-terrorists-reputation-chosen.trycloudflare.com/app/; приложение и tunnel healthy, Gemini photo grading и tutor проверены реальными provider calls, persistent PostgreSQL и uploads при cutover не менялись.
- Next: Провести наблюдаемую учебную сессию с реальным учеником и измерить время до первой самостоятельной отправки фото, число запросов подсказки и долю успешных transfer-задач.
<!-- codex-wrap:1236e4a74b02ad29223d:end -->

<!-- codex-wrap:f245ad18c9d5809dcf16:begin -->
## 2026-07-20 - AI принимает эквивалентный typed-ответ

- Why: Gemini ошибочно отклонял математически верный ответ 2 5/6 только из-за требуемой формы 17/6.
- Result: Production r21 развёрнут поверх прежнего online-образа; реальный POST /api/journey/answer трижды получил от Gemini correct+format для 2 5/6, сохранил problem/stage и не изменил mastery.
- Next: Пользователю обновить текущий экран и повторить 2 5/6; приложение должно показать, что смысл верный, и попросить только нужную форму записи.
<!-- codex-wrap:f245ad18c9d5809dcf16:end -->

<!-- codex-wrap:9c7ad11f9c9d43a05452:begin -->
## 2026-07-20 - Production answer-or-photo mobile learning flow

- Why: Довести учебный CJM до production: AI-проверка печатного ответа без обязательного фото, равноправный photo-flow и устойчивый mobile UX с живой keyboard-проверкой.
- Result: Правильный печатный ответ завершает задачу без фото; incorrect/uncertain сохраняют контекст и восстанавливаются; HEIC/JPEG photo-flow, AI tutor, idempotency/reload/race recovery и 375/844/932/1280 layouts проверены. Public mobile WebKit с реальной OS keyboard подтвердил видимые input, feedback и действия. Reviewer: READY, оставшихся P0/P1 нет.
- Next: Дать public приложение первой небольшой группе учеников и собрать продуктовые метрики реальной учебной сессии без изменения принятого answer-or-photo контракта.
<!-- codex-wrap:9c7ad11f9c9d43a05452:end -->
