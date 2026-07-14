---
name: kodi-webapp-v6-canon
description: kodi-web webapp/ дизайн-канон v6 «Тетрадь чемпиона» — токены, signature RouteSpine, шрифт-каскад, DEV-мок паттерн
metadata:
  type: project
---

Боевой React-PWA `webapp/` живёт по канону **v6 «Тетрадь чемпиона»** (регистр warm-craft), портирован из победившего концепта K-B в R2 (2026-07-13). Старый `DESIGN_SYSTEM.md` — архив v5 со STOP-баннером; действующий бриф — `docs/loops/runs/2026-07-13-webapp-v6/DESIGN-V6.md`.

**Токены = LAW** в `src/theme/tokens.css` (единственный источник сырых hex/px, исключён из `lint:design`). v6 добавил: ink-пары `--brand-ink/--attn-ink/--success-ink` (AA-текст на светлом), слои бумаги `--paper/-2/-3/--surface`, клетку `--grid/--grid-strong`, `--on-brand=ink` (ink-на-оранже, НЕ белый — AA 7:1), `--font-display`. Компоненты — только `var(--token)`/Tailwind-утилиты; сырой hex/px в `src/**` ловит гейт.

**Signature = «маршрут маркером по клетке»** (`src/components/route/`): `RouteSpine` (вертикаль hub/drill) + `RouteMeter` (горизонталь среза) рисуют рукописную оранжевую кривую по РЕАЛЬНЫМ центрам DOM-узлов (`useRoutePath`: Q-сегменты + детерминированный sin-hash wobble), пройдено=solid (stroke-dashoffset draw), впереди=пунктир. reduced-motion → мгновенно. Оранж = ТОЛЬКО маршрут/прогресс/primary-CTA; бейджи/табы/сегменты — ink-пары/soft/белый чип.

**Шрифт-каскад** (гоча): пара `'Unbounded'`(display) + `'Golos Text'`(body), оба self-hosted. Unbounded-сабсет НЕ содержит казах. **Ң (U+04A2)** и №(U+2116) → каскад `'Unbounded','Golos Text',sans-serif` роняет их на Golos автоматически (per-glyph fallback). Верификация — dual-fallback spread Playwright'ом на живом app (ВЕРШИНА spread≠0 = Unbounded применён; Ң spread=0 = чистый fallback, не тофу), НЕ `fonts.check`-self-report.

**DEV-мок для offline self-render**: `lib/api.ts` + `lib/devMocks.ts`, gated `import.meta.env.DEV && MODE!=='test'` (52 vitest-теста не задевает — в test-режиме fetch мокается). Даёт живые скрины срез/прогресс/закрепление без бэка. Self-render: `localStorage['kodi.jwt']` непустой → RequireAuth пропускает → DEV-мок. Кёди — ТОЛЬКО SVG из `Mascot.tsx`. Ap-контракты пропсов НЕ ломать (см. [[kodi-web-design-v5-rails]]).
