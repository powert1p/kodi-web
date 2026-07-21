# Concept directions — одинаковая truth, три разные системы

## Shared fixture

Ученик: Саша, 6 класс. Тема: `Доли от оставшейся части`. Режим: самостоятельная задача.

Задача:

> В школьной библиотеке 3/8 всех книг — приключения. Из оставшихся книг 2/5 —
> научно-популярные. Какая доля всех книг относится к научно-популярным?

Truth gate: остаток `1 − 3/8 = 5/8`; доля от остатка `5/8 × 2/5 = 1/4`.

## Frozen state matrix

Каждое направление рендерит одинаковую задачу и пять состояний на обоих viewport — 10 renders на
direction, 30 total:

1. `independent` — task + photo-default dock + visible typed alternative;
2. `needs_revision` — AI просит доработать первый смысловой шаг; task/attempt остаются видимы;
3. `hint_h2` — открыт Socratic strategy question, ответ не раскрыт;
4. `tutor_open` — contextual AI thread с provenance `эта задача · шаг 1`;
5. `uncertain` — сохранённое фото + reason `unreadable` + rephoto/retype recovery.

В каждом state видимы task, mode и next action. State matrix этого run явно заменяет legacy
`hub/drill/srez` screenshot set из общей rubric: цель run — workspace, а не legacy routes.

## Frozen global register

**Собранный**; запрещены card soup, full-screen state replacement и mascot/display-first.

## A — «Поля мысли»

1. **Register + defaults:** собранный; без школьного бланка, sepia nostalgia и card grid.
2. **Direction/spatial:** один широкий учебный лист; условие и попытка идут по центральной
   колонке, feedback живёт на боковом поле и соединяется с конкретным шагом. Mobile складывает
   поле в локальную заметку сразу под проблемным фрагментом, а не в отдельную страницу.
3. **Fonts:** Literata for short editorial headings/math emphasis; Golos Text for UI/body.
4. **Palette:** paper `#F7F1E7`, ink `#18342D`, ember `#E97624`, sage `#DCE8E0`, pencil
   `#66736E`; orange only action/annotation.
5. **Signature:** code-native `смысловая скобка` — вертикальная bracket соединяет phrase
   «из оставшихся», AI evidence и retry action.
6. **Asset:** one CSS/vector margin-bracket composition; no raster, mascot or copied logo.
7. **Layout/rhythm:** editorial 12-column desktop sheet with 64 px margin; mobile 20 px edge,
   24/36/56 rhythm, compact sticky response dock.

## B — «Точный верстак»

1. **Register + defaults:** собранный; без SaaS dashboard, heavy chrome и floating widget soup.
2. **Direction/spatial:** desktop is a true three-zone workbench: narrow session rail, dominant
   task/work canvas, dedicated tutor/evidence rail. Mobile becomes one canvas with a compact
   segmented control and dock; rails turn into anchored sheets, not stacked cards.
3. **Fonts:** Alumni Sans for terse stage labels/numerals; Onest for task/UI; Golos fallback.
4. **Palette:** chalk `#F4F3EC`, graphite `#152E2A`, signal `#F07F24`, mineral `#D7E3DF`, cobalt
   ink `#315E62`; high precision without corporate blue.
5. **Signature:** code-native `рамка шага` — four corner marks lock onto the reasoning fragment AI
   evaluated and follow it from task to feedback.
6. **Asset:** one responsive focus-frame drawn in CSS/SVG; no raster or decorative telemetry.
7. **Layout/rhythm:** dense but calm 96/1fr/320 desktop grid; 16 px mobile gutters, 8 px micro,
   24 px component and 48 px section rhythm.

## C — «Нить решения»

1. **Register + defaults:** собранный; без candy path, numbered lesson cards и decorative
   progress bar.
2. **Direction/spatial:** the page is one continuous reasoning path: condition → learner work →
   AI evidence → next action. Desktop path travels horizontally through an open canvas; mobile
   rotates into a vertical trace. Feedback is part of the path, not a panel beside it.
3. **Fonts:** M PLUS Rounded for warm short headings/numerals; Onest for body/math/UI.
4. **Palette:** milk `#FFF9EF`, pine `#173A31`, tangerine `#F58B2B`, mint `#DCECE4`, berry
   `#8F4C5B`; berry only for annotated mismatch, never page danger.
5. **Signature:** code-native `нить доказательства` — a single continuous line changes texture at
   AI-confirmed/uncertain segments and terminates at the only next action.
6. **Asset:** one SVG/CSS responsive proof-thread; no mascot, stock imagery or fake rewards.
7. **Layout/rhythm:** open asymmetric canvas, 72 px desktop stations along path; mobile 20 px
   gutter and 28/44 vertical cadence, dock integrated into final path node.

## Selection criteria

1. Orientation: task, mode and next action in five seconds.
2. Continuity: task remains visible and spatially stable during feedback/help.
3. Cognitive load: one primary CTA and compact, legible secondary controls.
4. Math focus: condition and learner reasoning dominate decoration/brand.
5. Submission clarity: photo default and typed alternative are understandable together.
6. Pedagogical clarity: feedback points to reasoning without leaking the answer.
7. Responsive accessibility: real mobile/desktop composition, targets/focus/overflow pass.
8. Premium distinctiveness: deliberate product-specific art direction, not generic cards.

The frozen rubric chooses one direction; palette preference cannot compensate for a broken flow.
