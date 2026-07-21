# Production child journey release — frozen brief

**Статус:** in progress  
**Цель:** безопасно довести текущий vertical kodi-web до онлайн-состояния, где ребёнок может пройти полезный урок, получить настоящий AI-разбор тетради и продолжить сократический диалог без утечки ответа.

## Пользователь и job

- Ученик 11–13 лет готовится к поступлению в НИШ в офлайн-центре AiPlus.
- Он решает математику в тетради с телефона и должен в любой момент понимать один следующий шаг.
- Продукт не заменяет живого учителя: он ведёт индивидуальную практику, локализует ошибку и возвращает ребёнка к самостоятельному решению.

## В scope

1. Основной путь: регистрация/вход → «Мой путь» → один authored-урок по смесям → guided practice → independent + transfer → сохранённый результат.
2. AI-разбор: согласие → загрузка безопасного тестового фото → настоящий Gemini verdict/diagnosis → multi-turn tutor → закрепление.
3. Ошибочные состояния: неверный PIN, нет согласия, плохой/большой файл, сеть, provider unavailable, stale/retry/reload.
4. Mobile 375×844 и desktop 1280×900: keyboard focus, touch targets, overflow, console/network errors.
5. Production: воспроизводимый deploy, health, секреты, transport security, rollback и повторный journey на сервере.

## Не выдаём за готовое

- Один урок не является полным курсом подготовки к НИШ.
- Synthetic/eval-фото не доказывают качество на реальных детских тетрадях.
- Green E2E не доказывает рост экзаменационного балла без pre/post-пилота.
- Legacy Flutter `/` и owner analytics не входят в основной детский journey.

## Frozen release bar

| Gate | Бинарное условие |
|---|---|
| G0 Mechanical | Backend DB suite без skip; frontend Vitest/typecheck/lint/design/build; Docker build; Flutter build проходит |
| G1 Main journey | Свежий и returning ученик проходят путь до результата; wrong/reload/retry/error/empty покрыты; 375/1280 без console/API/overflow ошибок |
| G2 Photo AI | Consent denial работает; invalid/oversize отклоняются; минимум match+mismatch фото проходят через **реальный Gemini**; результат сохраняется и соответствует контексту задачи |
| G3 Tutor AI | **Реальный** multi-turn tutor переиспользует session/history, даёт конкретный следующий приём, не раскрывает answer/expected value даже при прямой просьбе, provider failure честный |
| G4 Production safety | HTTPS для пользовательского трафика; app/DB не торчат наружу сырыми портами; `.env` 600; JWT/Gemini заданы; CORS/forwarded headers ограничены; health и rollback проверены |
| G5 Pedagogy | Проверка ответа code-side; LLM только объясняет; одна primary action; transfer обязателен; прогресс сохраняется; telemetry позволяет увидеть completion/help/retry |

## Вердикты

- `READY_FOR_CONTROLLED_PILOT`: G0–G5 зелёные, но пилот ограничен текущим authored vertical.
- `ONLINE_TECHNICAL_PREVIEW`: приложение онлайн, но хотя бы один из G2–G5 не закрыт.
- `NOT_READY`: есть P0 в correctness, privacy/security, AI grounding или сохранении результата.

После технического pilot gate отдельный outcome gate: расширить curriculum, собрать consented notebook eval-set, подтвердить ≥85% корректных verdicts и false-reject ≤5%, затем измерить baseline → practice → post-test.
