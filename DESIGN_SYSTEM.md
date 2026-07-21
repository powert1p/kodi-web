# kodi-web — маршрутизация дизайн-системы

> Обновлено: 2026-07-16. Этот файл не хранит отдельную палитру и не смешивает React PWA с
> legacy Flutter.

## Действующий продукт

Пользовательский тренажёр находится в `webapp/` и публикуется на `/app/`. Его единственный
maintenance-канон — [webapp/DESIGN_SYSTEM.md](webapp/DESIGN_SYSTEM.md); токены —
`webapp/src/theme/tokens.css`, шрифты — `webapp/src/theme/fonts.css`.

Перед UI-изменениями в `webapp/` читать:

1. `docs/VISION.md` — продуктовая рамка.
2. `docs/loops/DESIGN-FLOW.md` — routing между maintenance и clean-slate generator-loop.
3. `webapp/DESIGN_SYSTEM.md` — принятый v12 «Фокус-станция» для maintenance.
4. При активном redesign — frozen `contract.md`, `BRIEF.md` и `RUBRIC.md` конкретного run.

Явный отказ владельца от текущего вида временно превращает действующий канон в anti-reference;
после generator-loop сюда переносится только победивший проверенный production result.

## Legacy

`frontend/` — замороженный Flutter Web-клиент. Его Material 3/Roboto/blue-токены не применяются
к `webapp/`. Менять Flutter UI можно только по отдельной явной задаче и локальному канону.

## Проверка

Для `webapp/`: `npm run lint`, `npm run lint:design`, `npx tsc -b`, `npx vitest run`,
`npm run build`, затем production render на 375×844 и 1280×900 по state matrix без console,
request и horizontal-overflow ошибок.
