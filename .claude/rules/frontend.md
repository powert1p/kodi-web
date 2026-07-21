# kodi-web Frontend — React PWA

## Действующий клиент

- Продуктовый UI: `webapp/`, React 19 + TypeScript + Vite + Tailwind v4 + React Router 7 +
  TanStack Query + KaTeX, base `/app/`.
- Канон: `webapp/DESIGN_SYSTEM.md`; токены: `webapp/src/theme/`; UX-рамка: `docs/VISION.md`.
- API только через `webapp/src/lib/api.ts`/`auth.ts`, типы сверять с backend Pydantic.
- Ошибки запросов должны давать recovery action; mutations — pending и защита от double submit.
- Математика только через `MathText`; внутренние id и server-side ответы до попытки не показывать.

## Legacy Flutter

`frontend/` — замороженная learning-платформа. Не использовать её Material/Roboto/blue-токены
в `webapp/` и не менять без отдельной явной задачи.

## Проверка

Из `webapp/`: `npm run lint`, `npm run lint:design`, `npx tsc -b`, `npx vitest run`,
`npm run build`; затем реальный browser-render 375×844 и 1280×900, console и overflow.
