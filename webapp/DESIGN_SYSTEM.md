# DESIGN SYSTEM v12 — «Фокус-станция»

> Действующий канон React PWA `/app/`, 2026-07-16. Он принят из production-run
> `docs/loops/runs/2026-07-16-adaptive-photo-first-nis/` после полного state matrix,
> real-Gemini CJM и blind panel. V7–V11, tape-first layout и mascot-first композиции —
> historical/legacy, не источник решений для основного journey.

## 1. Характер

AiPlus — спокойная математическая станция подготовки к NIS для ребёнка 10–13 лет. Интерфейс
должен ощущаться дорогим и уверенным, но не официальным, не инфантильным и не похожим на
dashboard. На каждом экране сначала видны смысл этапа или математика, затем одно действие,
затем доказательство результата.

Визуальная формула: **warm cream + deep forest + дисциплинированный orange + evidence-контур**.
Orange обозначает действие или подтверждённый факт, но не заливает страницы. Иллюстрация и
персонаж не участвуют в primary journey.

## 2. Источники правды

- Product truth: `../docs/VISION.md` и `../docs/loops/runs/2026-07-16-adaptive-photo-first-nis/contract.md`.
- Frozen brief/rubric: `../docs/loops/runs/2026-07-16-adaptive-photo-first-nis/BRIEF.md` и `RUBRIC.md`.
- Цвет, type aliases, radii и shadows: `src/theme/tokens.css`.
- Self-hosted fonts: `src/theme/fonts.css`.
- Primary flow: `src/features/journey/` и `/login`; legacy review routes не задают новый канон.
- Production harness: `state_matrix_gate.py` и `live_cjm_gate.py` в active run.

Сырые hex и новые arbitrary color/px values вне theme запрещены. Для нового UI использовать
semantic `--focus-*` tokens; старые aliases остаются только для постепенной миграции legacy
routes.

## 3. Brand и персонажи

- `BrandMark` — самостоятельный code-native знак; исходный прямоугольный логотип нельзя
  вставлять, трассировать или повторять один в один.
- На `/`, `/login`, diagnostic, lesson, photo, guided, transfer и result персонажа нет.
- Существующие squirrel assets и `Mascot` допустимы только в historical `/review` routes до их
  миграции; они не должны возвращаться в primary journey, условие задачи или CTA.
- Brand занимает служебную роль. Он не конкурирует с математикой и не обещает fake reward.

## 4. Типографика и математика

- **Alumni Sans Variable** — route/result/transition headings и короткие stage marks.
- **Onest Variable** — условия, инструкции, формы, controls и весь длинный текст.
- **Golos Text** — fallback для кириллицы и казахских glyphs.
- **Tektur Variable** — compatibility-only для legacy v11; в новом journey не использовать.
- Крупный display не применяется к условию задачи: condition и diagnostic question визуально
  старше декора. Учебный текст не меньше 18 px.
- Формула не получает декоративный pill. Page-level horizontal overflow запрещён; локальный
  scroller допустим только для действительно длинной формулы и доступен с keyboard.

## 5. Цвет и материал

- Base: `--focus-paper`, `--focus-surface`, `--focus-ink`.
- Orange: `--focus-orange` для primary CTA и evidence event; orange wall запрещён.
- Teal: support/recovery/confirmed evidence. Danger: только локальная recoverable ошибка.
- Материал — открытая кремовая плоскость, тонкий контур и редкая мягкая тень.
- Card soup, bento, glass, generic AI-gradient, SaaS blue и dark luxury-stage запрещены.

## 6. Signature: evidence-контур

Круги, дуги и progress marks показывают только серверные факты:

1. место ученика в последовательности adaptation → diagnostic → route → lesson;
2. текущий режим independent/guided/transfer;
3. количество AI-confirmed самостоятельных outcomes и mastery evidence;
4. recovery без ложного штрафа при unreadable/uncertain/provider error.

Guided и supported practice никогда не окрашиваются как mastery. Для одной самостоятельной задачи
первый AI-confirmed `incorrect` и первый `correct` outcome учитываются по одному разу: фото
показывает ход, typed answer проверяет итог. После поддержки доказательство появляется только
после новой independent transfer-задачи.

## 7. Композиция

- Mobile 375×844 — primary: одна задача, одно доминирующее действие, touch target ≥44 px.
- Short landscape 844×375 и 932×430 — typed form живёт в document flow: fixed dock не обрезает
  input, submit, photo или help.
- Desktop 1280×900 — самостоятельная двухзонная композиция, а не растянутый mobile stack.
- Регистрация ведёт в адаптацию, затем diagnostic, result, персональный route и явный start.
- В photo-default уроке условие и самостоятельная попытка главнее инструкции, controls и progress;
  typed и photo остаются равноправно доступными способами завершить текущую задачу.
- «Не знаю, как решать» — вторичное явное действие. До нажатия guided UI не показывается.
- Persistent каталог функций, AI-chat и нижняя навигация не конкурируют с учебным экраном.

## 8. UX и state grammar

- Server journey — source of truth; refresh/relogin возвращают в точный сохранённый state.
- Stale `409` применяет `error.state` сервера без ложного success; typed draft сохраняется для той
  же задачи. Offline/timeout/429/503 сохраняют draft и durable client attempt id для retry.
- Loading сохраняет геометрию. Error сообщает, что сохранено, и даёт одно recovery action.
- Unreadable/uncertain/wrong-photo/provider/offline не становятся математической ошибкой.
- Pending photo привязан к identity + journey + problem и не переносится между аккаунтами.
- Photo default: одно фото всего решения проверяет ход. Typed correct атомарно открывает transfer
  (или topic result) без обязательного фото; typed needs_revision/uncertain оставляют ту же задачу
  с photo и help. Guided использует typed/options без фото шагов.
- Mastery требует probability ≥0.85, минимум три самостоятельных correct и accuracy ≥0.5;
  diagnostic threshold 0.7 остаётся отдельной семантикой.
- После typed advance focus переходит на heading новой задачи. Видимый focus, `aria-live`, reduced
  motion и отсутствие page overflow обязательны.

## 9. Production gates

```bash
npm run lint
npm run lint:design
npx tsc -b
npx vitest run
npm run build
```

Затем обязательны state matrix на 375×844 и 1280×900, truth-gate математики, console/request/
overflow/focus/touch/reduced-motion checks, real Gemini для readable/unreadable/retry и полный CJM
с двумя диагностическими профилями. Frozen READY: у каждого из трёх blind judges каждая ось
≥8.0, average ≥8.5, `math_focus` и `premium_distinctiveness` ≥8.5, минимум 2/3 `wow=true`, все
три verdict `READY`.
